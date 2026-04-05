"""ProxyService: manages MTProto proxy subscriptions via mtg-agent API."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import aiohttp
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import Settings
from db.dal import proxy_subscription_dal
from db.models import ProxySubscription

log = logging.getLogger(__name__)


class ProxyService:
    def __init__(self, settings: Settings, bot: Bot):
        self.settings = settings
        self.bot = bot
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def base_url(self) -> str:
        return (self.settings.PROXY_AGENT_URL or "").rstrip("/")

    @property
    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self.settings.PROXY_AGENT_TOKEN}"}

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15),
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    # --- mtg-agent HTTP methods ---

    async def _agent_create_secret(self, traffic_limit_bytes: int, telegram_id: int = None) -> Dict[str, Any]:
        session = await self._get_session()
        body = {"traffic_limit_bytes": traffic_limit_bytes}
        if telegram_id:
            body["telegram_id"] = telegram_id
        async with session.post(
            f"{self.base_url}/api/secrets", json=body, headers=self.headers,
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def _agent_delete_secret(self, secret: str):
        session = await self._get_session()
        async with session.delete(
            f"{self.base_url}/api/secrets/{secret}", headers=self.headers,
        ) as resp:
            resp.raise_for_status()

    async def _agent_get_stats(self, secret: str) -> Dict[str, Any]:
        session = await self._get_session()
        async with session.get(
            f"{self.base_url}/api/secrets/{secret}/stats", headers=self.headers,
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def _agent_reset_traffic(self, secret: str):
        session = await self._get_session()
        async with session.post(
            f"{self.base_url}/api/secrets/{secret}/reset-traffic", headers=self.headers,
        ) as resp:
            resp.raise_for_status()

    # --- Business logic ---

    async def activate_proxy(
        self,
        session: AsyncSession,
        user_id: int,
        traffic_gb: float,
        days: int,
        is_promo: bool = False,
    ) -> Optional[ProxySubscription]:
        """Create a new proxy subscription for the user."""
        traffic_limit_bytes = int(traffic_gb * 1024 ** 3)
        end_date = datetime.now(timezone.utc) + timedelta(days=days)

        try:
            agent_resp = await self._agent_create_secret(
                traffic_limit_bytes=traffic_limit_bytes,
                telegram_id=user_id,
            )
        except Exception as e:
            log.error("Failed to create proxy secret for user %s: %s", user_id, e)
            return None

        secret = agent_resp["secret"]
        tg_link = agent_resp["tg_link"]

        proxy_sub = await proxy_subscription_dal.create_proxy_subscription(
            session=session,
            user_id=user_id,
            secret=secret,
            tg_proxy_link=tg_link,
            traffic_limit_bytes=traffic_limit_bytes,
            end_date=end_date,
            is_promo=is_promo,
        )
        await session.commit()

        log.info(
            "Activated proxy for user %s: %s, %s GB, %d days, promo=%s",
            user_id, secret[:8], traffic_gb, days, is_promo,
        )
        return proxy_sub

    async def activate_promo_proxy(
        self, session: AsyncSession, user_id: int
    ) -> Optional[ProxySubscription]:
        """Activate free promo proxy (5 GB) for existing VPN users."""
        # Check eligibility
        has_vpn = await proxy_subscription_dal.has_any_subscription(session, user_id)
        if not has_vpn:
            return None

        already_claimed = await proxy_subscription_dal.has_proxy_promo(session, user_id)
        if already_claimed:
            return None

        return await self.activate_proxy(
            session=session,
            user_id=user_id,
            traffic_gb=self.settings.PROXY_PROMO_FREE_GB,
            days=self.settings.PROXY_PROMO_FREE_DAYS,
            is_promo=True,
        )

    async def deactivate_proxy(self, session: AsyncSession, proxy_sub_id: int):
        """Deactivate proxy subscription."""
        proxy_sub = await session.get(ProxySubscription, proxy_sub_id)
        if not proxy_sub:
            return

        try:
            await self._agent_delete_secret(proxy_sub.secret)
        except Exception as e:
            log.warning("Failed to delete secret on agent: %s", e)

        await proxy_subscription_dal.deactivate_proxy_subscription(session, proxy_sub_id)
        await session.commit()

    async def sync_traffic(self, session: AsyncSession, proxy_sub: ProxySubscription):
        """Sync traffic from agent and deactivate if limit exceeded."""
        try:
            stats = await self._agent_get_stats(proxy_sub.secret)
        except Exception as e:
            log.warning("Failed to get stats for %s: %s", proxy_sub.secret[:8], e)
            return

        used = stats.get("traffic_used_bytes", 0)
        await proxy_subscription_dal.update_proxy_traffic(
            session, proxy_sub.proxy_sub_id, used
        )

        # Check if exceeded
        if proxy_sub.traffic_limit_bytes > 0 and used >= proxy_sub.traffic_limit_bytes:
            log.info("Proxy %s exceeded limit, deactivating", proxy_sub.secret[:8])
            await proxy_subscription_dal.deactivate_proxy_subscription(
                session, proxy_sub.proxy_sub_id
            )

        await session.commit()

    async def get_active_for_user(
        self, session: AsyncSession, user_id: int
    ) -> Optional[ProxySubscription]:
        return await proxy_subscription_dal.get_active_proxy_subscription(session, user_id)
