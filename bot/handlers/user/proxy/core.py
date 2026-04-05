"""Proxy menu: show status, packages, promo."""

import logging
from typing import Optional

from aiogram import Router, F, types
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import Settings
from bot.services.proxy_service import ProxyService
from bot.middlewares.i18n import JsonI18n
from db.dal import proxy_subscription_dal

router = Router(name="user_proxy_core_router")


def _fmt_bytes(b: int) -> str:
    if b <= 0:
        return "0"
    gb = b / (1024 ** 3)
    if gb >= 1:
        return f"{gb:.2f} ГБ"
    mb = b / (1024 ** 2)
    return f"{mb:.0f} МБ"


@router.callback_query(F.data == "main_action:proxy")
async def proxy_menu_handler(
    callback: types.CallbackQuery,
    settings: Settings,
    i18n_data: dict,
    session: AsyncSession,
    proxy_service: ProxyService,
):
    lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    _ = lambda key, **kw: i18n.gettext(lang, key, **kw) if i18n else key

    active_sub = await proxy_service.get_active_for_user(session, callback.from_user.id)

    builder = InlineKeyboardBuilder()

    if active_sub:
        # Show status
        used = _fmt_bytes(active_sub.traffic_used_bytes or 0)
        limit = _fmt_bytes(active_sub.traffic_limit_bytes)
        end = active_sub.end_date.strftime("%d.%m.%Y")
        pct = 0
        if active_sub.traffic_limit_bytes > 0:
            pct = min(100, round((active_sub.traffic_used_bytes or 0) / active_sub.traffic_limit_bytes * 100))

        text = _(
            "proxy_status_message",
            used=used,
            limit=limit,
            pct=pct,
            end_date=end,
        )

        builder.row(InlineKeyboardButton(
            text=_("proxy_copy_link_button"),
            callback_data=f"proxy_action:copy_link",
        ))
        builder.row(InlineKeyboardButton(
            text=_("proxy_buy_more_button"),
            callback_data="proxy_action:buy",
        ))
    else:
        text = _("proxy_no_active_message")

        # Buy packages
        builder.row(InlineKeyboardButton(
            text=_("proxy_buy_button"),
            callback_data="proxy_action:buy",
        ))

    # Promo button (if eligible)
    if settings.PROXY_ENABLED and settings.PROXY_PROMO_FREE_GB > 0:
        has_promo = await proxy_subscription_dal.has_proxy_promo(session, callback.from_user.id)
        if not has_promo:
            has_vpn = await proxy_subscription_dal.has_any_subscription(session, callback.from_user.id)
            if has_vpn:
                builder.row(InlineKeyboardButton(
                    text=_("proxy_promo_button", gb=settings.PROXY_PROMO_FREE_GB),
                    callback_data="proxy_action:promo",
                ))

    builder.row(InlineKeyboardButton(
        text=_("back_to_main_menu_button"),
        callback_data="main_action:back_to_main",
    ))

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except Exception:
        await callback.message.answer(text, reply_markup=builder.as_markup())
    try:
        await callback.answer()
    except Exception:
        pass


@router.callback_query(F.data == "proxy_action:copy_link")
async def proxy_copy_link_handler(
    callback: types.CallbackQuery,
    settings: Settings,
    i18n_data: dict,
    session: AsyncSession,
    proxy_service: ProxyService,
):
    lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    _ = lambda key, **kw: i18n.gettext(lang, key, **kw) if i18n else key

    active_sub = await proxy_service.get_active_for_user(session, callback.from_user.id)
    if not active_sub:
        await callback.answer(_("proxy_no_active_message"), show_alert=True)
        return

    await callback.message.answer(
        _("proxy_link_message", link=active_sub.tg_proxy_link),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "proxy_action:promo")
async def proxy_promo_handler(
    callback: types.CallbackQuery,
    settings: Settings,
    i18n_data: dict,
    session: AsyncSession,
    proxy_service: ProxyService,
):
    lang = i18n_data.get("current_language", settings.DEFAULT_LANGUAGE)
    i18n: Optional[JsonI18n] = i18n_data.get("i18n_instance")
    _ = lambda key, **kw: i18n.gettext(lang, key, **kw) if i18n else key

    proxy_sub = await proxy_service.activate_promo_proxy(session, callback.from_user.id)

    if proxy_sub is None:
        await callback.answer(_("proxy_promo_not_eligible"), show_alert=True)
        return

    text = _(
        "proxy_promo_success",
        gb=settings.PROXY_PROMO_FREE_GB,
        days=settings.PROXY_PROMO_FREE_DAYS,
        link=proxy_sub.tg_proxy_link,
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=_("back_to_main_menu_button"),
        callback_data="main_action:back_to_main",
    ))

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()
