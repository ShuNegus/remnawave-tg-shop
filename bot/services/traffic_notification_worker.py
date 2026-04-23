"""Periodic worker that checks traffic usage and sends notifications at 90% threshold."""

import asyncio
import logging
from datetime import datetime, timezone

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.middlewares.i18n import JsonI18n
from bot.services.panel_api_service import PanelApiService
from config.settings import Settings
from db.dal import subscription_dal, user_dal


class TrafficNotificationWorker:

    def __init__(
        self,
        bot: Bot,
        settings: Settings,
        i18n: JsonI18n,
        panel_service: PanelApiService,
        session_factory: async_sessionmaker,
    ):
        self.bot = bot
        self.settings = settings
        self.i18n = i18n
        self.panel_service = panel_service
        self.session_factory = session_factory
        self._task: asyncio.Task | None = None

    async def start(self):
        self._task = asyncio.create_task(self._loop())
        logging.info("TrafficNotificationWorker started (interval=%dm, threshold=%.0f%%)",
                     self.settings.TRAFFIC_NOTIFICATION_CHECK_INTERVAL_MINUTES,
                     self.settings.TRAFFIC_NOTIFICATION_THRESHOLD * 100)

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logging.info("TrafficNotificationWorker stopped.")

    async def _loop(self):
        interval = self.settings.TRAFFIC_NOTIFICATION_CHECK_INTERVAL_MINUTES * 60
        while True:
            try:
                await self._check_all_users()
            except Exception:
                logging.exception("TrafficNotificationWorker: error in check cycle")
            await asyncio.sleep(interval)

    async def _check_all_users(self):
        threshold = self.settings.TRAFFIC_NOTIFICATION_THRESHOLD

        # Get all users from panel
        try:
            panel_data = await self.panel_service._request("GET", "/users", params={"size": 1000})
            if not panel_data or "response" not in panel_data:
                logging.warning("TrafficNotificationWorker: failed to fetch panel users")
                return
            panel_users = panel_data["response"].get("users", [])
        except Exception:
            logging.exception("TrafficNotificationWorker: failed to fetch panel users")
            return

        notified_count = 0
        async with self.session_factory() as session:
            for pu in panel_users:
                try:
                    await self._check_user(session, pu, threshold)
                    notified_count_delta = 1  # placeholder for counting
                except Exception:
                    logging.exception("TrafficNotificationWorker: error checking user %s", pu.get("username"))

            await session.commit()
        logging.debug("TrafficNotificationWorker: check cycle complete")

    async def _check_user(self, session: AsyncSession, panel_user: dict, threshold: float):
        traffic_info = panel_user.get("userTraffic") or {}
        used = traffic_info.get("usedTrafficBytes") or 0
        limit = panel_user.get("trafficLimitBytes") or 0

        if limit <= 0 or used <= 0:
            return

        usage_ratio = used / limit
        if usage_ratio < threshold:
            return

        # Find local user by telegram_id
        telegram_id = panel_user.get("telegramId")
        if not telegram_id:
            return

        # Check if we already notified for this subscription period
        sub = await subscription_dal.get_active_subscription_by_user_id(session, telegram_id)
        if not sub or not sub.is_active:
            return

        # skip_notifications check
        if sub.skip_notifications:
            return

        # Already notified for this billing cycle. Purchase/extension code
        # must reset last_notification_sent to None to re-enable notifications.
        if sub.last_notification_sent is not None:
            return

        # Send notification
        db_user = await user_dal.get_user_by_id(session, telegram_id)
        lang = (db_user.language_code if db_user else None) or self.settings.DEFAULT_LANGUAGE
        get_text = lambda key, **kw: self.i18n.gettext(lang, key, **kw)

        def _fmt_gb(val):
            gb = float(val) / (1024 ** 3)
            return f"{gb:.2f} GB"

        end_date_str = sub.end_date.strftime("%d.%m.%Y") if sub.end_date else "N/A"

        text = get_text(
            "traffic_90_notification",
            traffic_used=_fmt_gb(used),
            traffic_limit=_fmt_gb(limit),
            end_date=end_date_str,
        )

        try:
            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=get_text("buy_more_gb_button"),
                    callback_data="main_action:subscribe",
                )]
            ])
            await self.bot.send_message(telegram_id, text, reply_markup=kb, parse_mode="HTML")
            logging.info("Traffic notification sent to user %s (%.0f%% used)", telegram_id, usage_ratio * 100)
        except Exception:
            logging.warning("Failed to send traffic notification to user %s", telegram_id)
            return

        # Mark as notified
        await subscription_dal.update_subscription_notification_time(
            session, sub.subscription_id, datetime.now(timezone.utc)
        )
