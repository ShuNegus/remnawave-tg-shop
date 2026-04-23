"""Recover Telegram Stars payments stuck in pending_stars.

Когда прокси-хэндлер перехватывал все successful_payment, VPN-платежи
не обрабатывались: списание в Telegram прошло, но status=pending_stars
в БД и подписка не активирована.

Использование (внутри контейнера бота или локально с теми же env):

    # dry-run — показать кандидатов
    python -m scripts.recover_stuck_stars_payments

    # активировать конкретные платежи
    python -m scripts.recover_stuck_stars_payments --payment-ids 123,124 --apply

    # активировать все пэндинги начиная с даты, уведомить юзеров и админ-лог
    python -m scripts.recover_stuck_stars_payments \
        --since 2026-04-05 --apply --notify-user --notify-admin
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone
from typing import List, Optional

from dotenv import load_dotenv
from sqlalchemy import and_, select

from config.settings import get_settings
from db.database_setup import init_db_connection
from db.dal import payment_dal, user_dal
from db.models import Payment


def _parse_int_list(raw: Optional[str]) -> List[int]:
    if not raw:
        return []
    out: List[int] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if chunk:
            out.append(int(chunk))
    return out


def _parse_since(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    return datetime.strptime(raw, "%Y-%m-%d").replace(tzinfo=timezone.utc)


async def _fetch_candidates(
    session,
    since: Optional[datetime],
    payment_ids: List[int],
    user_ids: List[int],
) -> List[Payment]:
    conditions = [
        Payment.provider == "telegram_stars",
        Payment.status == "pending_stars",
        Payment.product_type == "vpn",
    ]
    if since:
        conditions.append(Payment.created_at >= since)
    if payment_ids:
        conditions.append(Payment.payment_id.in_(payment_ids))
    if user_ids:
        conditions.append(Payment.user_id.in_(user_ids))

    stmt = (
        select(Payment)
        .where(and_(*conditions))
        .order_by(Payment.created_at.asc())
    )
    return list((await session.execute(stmt)).scalars().all())


def _print_table(rows: List[Payment]):
    if not rows:
        print("No candidates found.")
        return
    print(f"{'payment_id':<10} {'user_id':<14} {'months/gb':<10} {'amount':<10} {'created_at':<20} description")
    print("-" * 120)
    for p in rows:
        created = p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else "-"
        print(
            f"{p.payment_id:<10} {p.user_id:<14} {str(p.subscription_duration_months):<10} "
            f"{str(p.amount):<10} {created:<20} {p.description or ''}"
        )


async def _activate_one(
    session,
    payment: Payment,
    subscription_service,
    referral_service,
    settings,
    sale_mode_override: Optional[str],
) -> Optional[dict]:
    """Mimic StarsService.process_successful_payment without the telegram Message."""
    amount = int(payment.amount)

    sale_mode = sale_mode_override or ("traffic" if settings.traffic_sale_mode else "subscription")
    months_value = payment.subscription_duration_months or 0
    traffic_gb = float(months_value) if sale_mode == "traffic" else None

    marker = f"recovered:{payment.payment_id}"
    marked = await payment_dal.mark_provider_payment_succeeded_once(
        session, payment.payment_id, marker
    )
    if not marked:
        logging.info("Payment %s already succeeded, skipping.", payment.payment_id)
        return None

    activation = await subscription_service.activate_subscription(
        session,
        payment.user_id,
        int(months_value) if sale_mode != "traffic" else 0,
        float(amount),
        payment.payment_id,
        promo_code_id_from_payment=payment.promo_code_id,
        provider="telegram_stars",
        sale_mode=sale_mode,
        traffic_gb=traffic_gb,
    )
    if not activation or not activation.get("end_date"):
        raise RuntimeError(f"activate_subscription returned empty for payment {payment.payment_id}")

    referral_bonus = None
    if sale_mode != "traffic":
        referral_bonus = await referral_service.apply_referral_bonuses_for_payment(
            session,
            payment.user_id,
            int(months_value) or 1,
            current_payment_db_id=payment.payment_id,
            skip_if_active_before_payment=False,
        )

    await session.commit()
    return {
        "activation": activation,
        "referral_bonus": referral_bonus,
        "sale_mode": sale_mode,
        "months": months_value,
        "amount": amount,
    }


async def _notify_user(bot, settings, i18n, session, payment: Payment, result: dict):
    try:
        from bot.utils.config_link import prepare_config_links
        from bot.keyboards.inline.user_keyboards import get_connect_and_main_keyboard

        db_user = await user_dal.get_user_by_id(session, payment.user_id)
        lang = (db_user.language_code if db_user and db_user.language_code
                else settings.DEFAULT_LANGUAGE)
        _ = lambda k, **kw: i18n.gettext(lang, k, **kw) if i18n else k

        activation = result["activation"]
        raw_link = activation.get("subscription_url")
        config_link_display, connect_button_url = await prepare_config_links(settings, raw_link)
        config_link_text = config_link_display or _("config_link_not_available")

        months = result["months"]
        if result["sale_mode"] == "traffic":
            text = _(
                "payment_successful_traffic_full",
                traffic_gb=str(int(months)) if float(months).is_integer() else f"{months:g}",
                end_date=activation["end_date"].strftime("%Y-%m-%d"),
                config_link=config_link_text,
            )
        else:
            text = _(
                "payment_successful_full",
                months=int(months),
                end_date=activation["end_date"].strftime("%Y-%m-%d"),
                config_link=config_link_text,
            )

        markup = get_connect_and_main_keyboard(
            lang, i18n, settings, config_link_display,
            connect_button_url=connect_button_url, preserve_message=True,
        )
        await bot.send_message(
            payment.user_id, text, reply_markup=markup,
            parse_mode="HTML", disable_web_page_preview=True,
        )
    except Exception as exc:
        logging.warning("Failed to notify user %s: %s", payment.user_id, exc)


async def _notify_admin(bot, settings, i18n, session, payment: Payment, result: dict):
    try:
        from bot.services.notification_service import NotificationService
        notification = NotificationService(bot, settings, i18n)
        user = await user_dal.get_user_by_id(session, payment.user_id)
        await notification.notify_payment_received(
            user_id=payment.user_id,
            amount=float(result["amount"]),
            currency="XTR",
            months=int(result["months"]) if result["sale_mode"] != "traffic" else 0,
            payment_provider="stars",
            username=user.username if user else None,
            traffic_gb=result["months"] if result["sale_mode"] == "traffic" else None,
        )
    except Exception as exc:
        logging.warning("Failed to notify admin for payment %s: %s", payment.payment_id, exc)


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", help="YYYY-MM-DD, нижняя граница created_at")
    parser.add_argument("--payment-ids", help="CSV payment_id")
    parser.add_argument("--user-ids", help="CSV user_id")
    parser.add_argument("--apply", action="store_true", help="Без флага — dry-run")
    parser.add_argument("--notify-user", action="store_true",
                        help="Отправить юзеру сообщение о успешной активации")
    parser.add_argument("--notify-admin", action="store_true",
                        help="Отправить нотификацию в админ лог-чат")
    parser.add_argument("--sale-mode", choices=["traffic", "subscription"],
                        help="Принудительно задать sale_mode (иначе авто по settings)")
    args = parser.parse_args()

    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )

    settings = get_settings()
    session_factory = init_db_connection(settings)
    if not session_factory:
        logging.critical("Failed to init DB connection")
        return 1

    since = _parse_since(args.since)
    payment_ids = _parse_int_list(args.payment_ids)
    user_ids = _parse_int_list(args.user_ids)

    async with session_factory() as session:
        candidates = await _fetch_candidates(session, since, payment_ids, user_ids)

    print(f"Found {len(candidates)} pending_stars VPN payment(s).")
    _print_table(candidates)

    if not args.apply:
        print("\n(dry-run) повтори с --apply для активации.")
        return 0
    if not candidates:
        return 0

    # Build services (lazy imports to avoid side-effects in dry-run)
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    from bot.services.panel_api_service import PanelApiService
    from bot.services.subscription_service import SubscriptionService
    from bot.services.referral_service import ReferralService

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    from bot.middlewares.i18n import get_i18n_instance
    i18n = get_i18n_instance(
        path="locales",
        default=settings.DEFAULT_LANGUAGE,
        domain="messages",
    )
    panel_service = PanelApiService(settings)
    subscription_service = SubscriptionService(settings, panel_service, bot, i18n)
    referral_service = ReferralService(settings, subscription_service, bot, i18n)

    ok, failed, skipped = 0, 0, 0
    try:
        for payment in candidates:
            async with session_factory() as session:
                try:
                    result = await _activate_one(
                        session, payment, subscription_service, referral_service,
                        settings, args.sale_mode,
                    )
                    if result is None:
                        skipped += 1
                        continue
                    ok += 1
                    logging.info(
                        "Recovered payment_id=%s user=%s end_date=%s",
                        payment.payment_id, payment.user_id,
                        result["activation"]["end_date"].strftime("%Y-%m-%d"),
                    )
                    if args.notify_admin:
                        await _notify_admin(bot, settings, i18n, session, payment, result)
                    if args.notify_user:
                        await _notify_user(bot, settings, i18n, session, payment, result)
                except Exception:
                    failed += 1
                    logging.exception("Failed to recover payment_id=%s", payment.payment_id)
                    await session.rollback()
    finally:
        try:
            await bot.session.close()
        except Exception:
            pass
        try:
            await panel_service.close_session()
        except Exception:
            pass

    print(f"\nDone. recovered={ok} failed={failed} skipped={skipped}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main()) or 0)
