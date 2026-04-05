"""Background worker that syncs proxy traffic and deactivates expired subscriptions."""

import asyncio
import logging
from datetime import datetime, timezone

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from config.settings import Settings
from bot.services.proxy_service import ProxyService
from db.dal import proxy_subscription_dal

log = logging.getLogger(__name__)


class ProxyTrafficWorker:
    def __init__(
        self,
        settings: Settings,
        proxy_service: ProxyService,
        async_session_factory: sessionmaker,
        bot: Bot,
    ):
        self.settings = settings
        self.proxy_service = proxy_service
        self.async_session_factory = async_session_factory
        self.bot = bot
        self._task = None

    async def start(self):
        if not self.settings.PROXY_ENABLED or self.proxy_service is None:
            return
        self._task = asyncio.create_task(self._loop())
        log.info("ProxyTrafficWorker started, interval=%d min",
                 self.settings.PROXY_TRAFFIC_CHECK_INTERVAL_MINUTES)

    async def stop(self):
        if self._task:
            self._task.cancel()
            self._task = None

    async def _loop(self):
        while True:
            try:
                await self._check_all()
            except Exception:
                log.exception("Error in proxy traffic worker")
            await asyncio.sleep(self.settings.PROXY_TRAFFIC_CHECK_INTERVAL_MINUTES * 60)

    async def _check_all(self):
        async with self.async_session_factory() as session:
            active_subs = await proxy_subscription_dal.get_all_active_proxy_subscriptions(session)
            now = datetime.now(timezone.utc)

            for sub in active_subs:
                # Check expiry
                if sub.end_date <= now:
                    log.info("Proxy sub %d expired, deactivating", sub.proxy_sub_id)
                    await self.proxy_service.deactivate_proxy(session, sub.proxy_sub_id)
                    continue

                # Sync traffic
                await self.proxy_service.sync_traffic(session, sub)

                # Notify at threshold
                if sub.traffic_limit_bytes > 0:
                    try:
                        stats = await self.proxy_service._agent_get_stats(sub.secret)
                        used = stats.get("traffic_used_bytes", 0)
                        pct = used / sub.traffic_limit_bytes
                        threshold = self.settings.TRAFFIC_NOTIFICATION_THRESHOLD

                        if pct >= threshold and (sub.traffic_used_bytes or 0) / sub.traffic_limit_bytes < threshold:
                            # Just crossed threshold
                            pct_display = round(pct * 100)
                            try:
                                await self.bot.send_message(
                                    sub.user_id,
                                    f"⚠️ Ваш TG прокси использовал {pct_display}% трафика.",
                                )
                            except Exception:
                                pass
                    except Exception:
                        pass
