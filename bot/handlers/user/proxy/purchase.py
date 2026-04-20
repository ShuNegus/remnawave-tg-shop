"""Proxy purchase: package selection and Stars payment."""

import logging
from typing import Optional

from aiogram import Router, F, types
from aiogram.types import InlineKeyboardButton, LabeledPrice
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import Settings
from bot.services.proxy_service import ProxyService
from bot.middlewares.i18n import JsonI18n
from db.dal import payment_dal
from db.models import Payment

router = Router(name="user_proxy_purchase_router")


@router.callback_query(F.data == "proxy_action:buy")
async def proxy_buy_menu_handler(
    callback: types.CallbackQuery,
    settings: Settings,
    i18n_data: dict,
):
    """Show proxy package options."""
    lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    _ = lambda key, **kw: i18n.gettext(lang, key, **kw) if i18n else key

    packages = settings.proxy_packages_parsed
    if not packages:
        await callback.answer(_("proxy_no_packages"), show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for pkg in packages:
        gb = pkg["gb"]
        price = pkg["price"]
        days = pkg["days"]
        gb_display = int(gb) if gb == int(gb) else gb
        builder.row(InlineKeyboardButton(
            text=_("proxy_package_button", gb=gb_display, days=days, price=price),
            callback_data=f"proxy_pay:{gb}:{price}:{days}",
        ))

    builder.row(InlineKeyboardButton(
        text=_("back_to_main_menu_button"),
        callback_data="main_action:proxy",
    ))

    text = _("proxy_select_package")
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except Exception:
        await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("proxy_pay:"))
async def proxy_pay_handler(
    callback: types.CallbackQuery,
    settings: Settings,
    i18n_data: dict,
    session: AsyncSession,
):
    """Create Stars invoice for proxy package."""
    lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    _ = lambda key, **kw: i18n.gettext(lang, key, **kw) if i18n else key

    try:
        _, gb_str, price_str, days_str = callback.data.split(":")
        gb = float(gb_str)
        stars_price = int(float(price_str))
        days = int(days_str)
    except (ValueError, IndexError):
        await callback.answer(_("error_try_again"), show_alert=True)
        return

    # Validate package exists server-side
    valid = any(
        p["gb"] == gb and p["price"] == stars_price and p["days"] == days
        for p in settings.proxy_packages_parsed
    )
    if not valid:
        await callback.answer(_("error_try_again"), show_alert=True)
        return

    user_id = callback.from_user.id
    gb_display = int(gb) if gb == int(gb) else gb
    description = _("proxy_payment_description", gb=gb_display, days=days)

    # Create payment record
    payment = Payment(
        user_id=user_id,
        amount=float(stars_price),
        currency="XTR",
        status="pending_stars",
        description=description,
        subscription_duration_months=0,
        provider="telegram_stars",
        product_type="proxy",
    )
    session.add(payment)
    await session.flush()

    # Send Stars invoice
    payload = f"{payment.payment_id}:{gb}:{days}:proxy"
    prices = [LabeledPrice(label=description, amount=stars_price)]

    try:
        await callback.bot.send_invoice(
            chat_id=user_id,
            title=description,
            description=description,
            payload=payload,
            provider_token=settings.STARS_PROVIDER_TOKEN or "",
            currency="XTR",
            prices=prices,
        )
        await session.commit()
    except Exception as e:
        logging.error("Failed to send proxy invoice: %s", e)
        await callback.answer(_("error_try_again"), show_alert=True)
        return

    # Confirmation message
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=_("back_to_main_menu_button"),
        callback_data="main_action:proxy",
    ))

    text = _("proxy_invoice_sent", gb=gb_display, days=days)
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except Exception:
        pass
    await callback.answer()


@router.pre_checkout_query(lambda q: q.invoice_payload.endswith(":proxy"))
async def proxy_pre_checkout_handler(pre_checkout: types.PreCheckoutQuery):
    await pre_checkout.answer(ok=True)


@router.message(F.successful_payment.invoice_payload.endswith(":proxy"))
async def proxy_successful_payment_handler(
    message: types.Message,
    settings: Settings,
    i18n_data: dict,
    session: AsyncSession,
    proxy_service: ProxyService,
):
    """Handle successful Stars payment for proxy."""
    payment = message.successful_payment
    if not payment or not payment.invoice_payload:
        return

    payload = payment.invoice_payload

    lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    _ = lambda key, **kw: i18n.gettext(lang, key, **kw) if i18n else key

    try:
        parts = payload.split(":")
        payment_db_id = int(parts[0])
        gb = float(parts[1])
        days = int(parts[2])
    except (ValueError, IndexError):
        logging.error("Invalid proxy payment payload: %s", payload)
        return

    # Mark payment as succeeded
    from sqlalchemy import update
    stmt = update(Payment).where(
        Payment.payment_id == payment_db_id,
        Payment.status == "pending_stars",
    ).values(status="succeeded")
    result = await session.execute(stmt)
    if result.rowcount == 0:
        logging.warning("Proxy payment %d already processed or not found", payment_db_id)
        return

    # Activate proxy
    proxy_sub = await proxy_service.activate_proxy(
        session=session,
        user_id=message.from_user.id,
        traffic_gb=gb,
        days=days,
    )

    if proxy_sub:
        gb_display = int(gb) if gb == int(gb) else gb
        end_date = proxy_sub.end_date.strftime("%d.%m.%Y")
        text = _(
            "proxy_payment_success",
            gb=gb_display,
            days=days,
            end_date=end_date,
            link=proxy_sub.tg_proxy_link,
        )
    else:
        text = _("proxy_activation_error")

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=_("back_to_main_menu_button"),
        callback_data="main_action:back_to_main",
    ))

    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
