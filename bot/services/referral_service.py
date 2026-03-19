import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, Dict, Any
from aiogram import Bot
from datetime import datetime, timezone, timedelta

from config.settings import Settings
from db.dal import user_dal
from db.dal import payment_dal
from db.models import User
from db.dal import subscription_dal
from bot.middlewares.i18n import JsonI18n
from .subscription_service import SubscriptionService


class ReferralService:

    def __init__(self, settings: Settings,
                 subscription_service: SubscriptionService, bot: Bot,
                 i18n: JsonI18n):
        self.settings = settings
        self.subscription_service = subscription_service
        self.bot = bot
        self.i18n = i18n

    async def apply_referral_bonuses_for_payment(
            self,
            session: AsyncSession,
            referee_user_id: int,
            purchased_subscription_months: int,
            current_payment_db_id: Optional[int] = None,
            skip_if_active_before_payment: bool = True) -> Dict[str, Any]:

        if not getattr(self.settings, "REFERRAL_ENABLED", True):
            return {
                "referee_bonus_applied_days": None,
                "referee_new_end_date": None,
                "inviter_bonus_applied_flag": False,
            }

        referee_final_end_date: Optional[datetime] = None
        referee_bonus_applied_days: Optional[int] = None
        inviter_bonus_successfully_applied = False

        try:
            referee_user_model = await user_dal.get_user_by_id(
                session, referee_user_id)
            if not referee_user_model or referee_user_model.referred_by_id is None:
                logging.debug(
                    f"User {referee_user_id} not referred or inviter ID missing. No referral bonuses."
                )
                return {
                    "referee_bonus_applied_days": None,
                    "referee_new_end_date": None
                }

            # If configured to apply referral bonuses only once per invited user,
            # check if the referee already has succeeded payments.
            # Use getattr with a safe default (True) to avoid AttributeError if
            # running with an older settings schema.
            if getattr(self.settings, "REFERRAL_ONE_BONUS_PER_REFEREE", True):
                try:
                    succeeded_count = await payment_dal.count_user_succeeded_payments(
                        session, referee_user_id, exclude_payment_id=current_payment_db_id
                    )
                    if succeeded_count and succeeded_count > 0:
                        logging.info(
                            f"Referral bonuses skipped for user {referee_user_id}: already has {succeeded_count} succeeded payments.")
                        return {
                            "referee_bonus_applied_days": None,
                            "referee_new_end_date": None
                        }
                except Exception as e_cnt:
                    logging.error(f"Failed counting succeeded payments for user {referee_user_id}: {e_cnt}")

            # Additionally, do not award referral bonuses if the user was active at payment time
            # (has an active subscription now). This avoids giving bonuses to already active users.
            if skip_if_active_before_payment:
                try:
                    if await self.subscription_service.has_active_subscription(session, referee_user_id):
                        logging.info(
                            f"Referral bonuses skipped for user {referee_user_id}: user currently has an active subscription.")
                        return {
                            "referee_bonus_applied_days": None,
                            "referee_new_end_date": None
                        }
                except Exception as e_sub:
                    logging.error(f"Failed to check active subscription for {referee_user_id}: {e_sub}")

            inviter_user_id = referee_user_model.referred_by_id
            inviter_user_model = await user_dal.get_user_by_id(
                session, inviter_user_id)

            referee_name_for_msg = referee_user_model.first_name or f"User {referee_user_id}"

            default_lang_for_placeholder = self.settings.DEFAULT_LANGUAGE
            inviter_name_for_referee_msg = (
                inviter_user_model.first_name if inviter_user_model
                and inviter_user_model.first_name else self.i18n.gettext(
                    default_lang_for_placeholder, "friend_placeholder"))

            # GB-based referral bonuses
            inviter_bonus = self.settings.referral_bonus_inviter  # {"gb": float, "days": int}
            referee_bonus = self.settings.referral_bonus_referee  # {"gb": float, "days": int}

            inviter_bonus_gb = inviter_bonus.get("gb", 0)
            inviter_bonus_days = inviter_bonus.get("days", 0)
            referee_bonus_gb = referee_bonus.get("gb", 0)
            referee_bonus_days_val = referee_bonus.get("days", 0)

            if inviter_bonus_gb > 0 and inviter_bonus_days > 0:
                if not inviter_user_model:
                    logging.warning(
                        f"Inviter user {inviter_user_id} not found in local DB. Cannot apply inviter bonus."
                    )
                else:
                    result = await self.subscription_service._activate_traffic_package(
                        session=session,
                        user_id=inviter_user_id,
                        traffic_gb=inviter_bonus_gb,
                        provider="referral",
                        override_days=inviter_bonus_days,
                    )
                    if result:
                        inviter_bonus_successfully_applied = True
                        logging.info(
                            f"Referral bonus of {inviter_bonus_gb} GB / {inviter_bonus_days} days applied for inviter {inviter_user_id}."
                        )
                        try:
                            inviter_lang = inviter_user_model.language_code or default_lang_for_placeholder
                            _i = lambda k, **kw: self.i18n.gettext(inviter_lang, k, **kw)
                            await self.bot.send_message(
                                inviter_user_id,
                                _i("referral_bonus_inviter_notification_traffic",
                                   gb=inviter_bonus_gb,
                                   days=inviter_bonus_days,
                                   referee_name=referee_name_for_msg))
                        except Exception as e_notify_inviter:
                            logging.error(
                                f"Failed to send bonus notification to inviter {inviter_user_id}: {e_notify_inviter}"
                            )
                    else:
                        logging.warning(
                            f"Failed to apply referral traffic bonus for inviter {inviter_user_id}."
                        )

            if referee_bonus_gb > 0 and referee_bonus_days_val > 0:
                result = await self.subscription_service._activate_traffic_package(
                    session=session,
                    user_id=referee_user_id,
                    traffic_gb=referee_bonus_gb,
                    provider="referral",
                    override_days=referee_bonus_days_val,
                )
                if result:
                    referee_final_end_date = result.get("end_date")
                    referee_bonus_applied_days = referee_bonus_days_val
                    logging.info(
                        f"Referral bonus of {referee_bonus_gb} GB / {referee_bonus_days_val} days applied for referee {referee_user_id}."
                    )
                else:
                    logging.warning(
                        f"Failed to apply referee bonus for {referee_user_id}."
                    )

            return {
                "referee_bonus_applied_days": referee_bonus_applied_days,
                "referee_new_end_date": referee_final_end_date,
                "inviter_bonus_applied_flag":
                inviter_bonus_successfully_applied
            }
        except Exception as e:
            logging.error(
                f"Error in apply_referral_bonuses_for_payment for referee {referee_user_id}: {e}",
                exc_info=True)

            raise

    async def generate_referral_link(self, session: AsyncSession,
                                     bot_username: str,
                                     inviter_user_id: int) -> Optional[str]:
        if not getattr(self.settings, "REFERRAL_ENABLED", True):
            return None

        try:
            user = await user_dal.get_user_by_id(session, inviter_user_id)
            if not user:
                logging.warning(
                    "Unable to generate referral link: user %s not found.",
                    inviter_user_id,
                )
                return None

            referral_code = await user_dal.ensure_referral_code(session, user)
            if not referral_code:
                logging.warning(
                    "User %s has no referral code even after regeneration attempt.",
                    inviter_user_id,
                )
                return None

            return f"https://t.me/{bot_username}?start=ref_u{referral_code}"
        except Exception as exc:
            logging.error(
                "Failed to generate referral link for user %s: %s",
                inviter_user_id,
                exc,
                exc_info=True,
            )
            return None

    async def get_referral_stats(self, session: AsyncSession, user_id: int) -> dict:
        """Get referral statistics for a user"""
        from db.dal import user_dal, payment_dal
        
        try:
            # Count total invited users (referrals)
            invited_count_result = await session.execute(
                text("SELECT COUNT(*) FROM users WHERE referred_by_id = :user_id"),
                {"user_id": user_id}
            )
            invited_count = invited_count_result.scalar() or 0
            
            # Count users who made successful payments (purchased subscription)
            purchased_count_result = await session.execute(
                text("""
                    SELECT COUNT(DISTINCT u.user_id) 
                    FROM users u 
                    JOIN payments p ON u.user_id = p.user_id 
                    WHERE u.referred_by_id = :user_id 
                    AND p.status = 'succeeded'
                """),
                {"user_id": user_id}
            )
            purchased_count = purchased_count_result.scalar() or 0
            
            return {
                "invited_count": invited_count,
                "purchased_count": purchased_count
            }
        except Exception as e:
            logging.error(f"Error getting referral stats for user {user_id}: {e}")
            return {
                "invited_count": 0,
                "purchased_count": 0
            }
