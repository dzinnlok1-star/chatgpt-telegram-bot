"""Subscription purchase flow: Telegram Stars + YooKassa."""

from __future__ import annotations

from datetime import UTC

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from app.config import Settings
from app.db import repositories as repo
from app.db.models import User
from app.db.session import SessionLocal
from app.i18n import translate
from app.keyboards.inline import (
    back_button,
    pay_methods_keyboard,
    tariffs_keyboard,
    yookassa_check_keyboard,
)
from app.logger import get_logger
from app.services.yookassa_service import YooKassaService

router = Router(name="billing")
logger = get_logger("billing")


@router.message(Command("buy"))
async def cmd_buy(message: Message, user: User, settings: Settings) -> None:
    await message.answer(
        translate(user.language, "buy_title"),
        reply_markup=tariffs_keyboard(user.language, settings.tariffs),
    )


@router.message(Command("subscription"))
async def cmd_subscription(message: Message, user: User, settings: Settings) -> None:
    await cmd_buy(message, user, settings)


@router.callback_query(F.data.startswith("buy:"))
async def cb_choose_tariff(
    call: CallbackQuery, user: User, settings: Settings, yookassa: YooKassaService
) -> None:
    assert call.data is not None
    code = call.data.split(":", 1)[1]
    tariff = settings.tariff_by_code(code)
    if tariff is None:
        await call.answer("Tariff not found", show_alert=True)
        return
    await call.answer()
    lang = user.language
    details = translate(
        lang,
        "buy_details",
        title=tariff.title,
        days=tariff.days,
        messages=tariff.messages,
        images=tariff.images,
        voices=tariff.voices,
        stars=tariff.price_stars,
        rub=tariff.price_rub,
    )
    await call.message.edit_text(
        details + "\n\n" + translate(lang, "buy_choose_method"),
        reply_markup=pay_methods_keyboard(
            lang, tariff.code, yookassa_enabled=yookassa.enabled
        ),
    )


@router.callback_query(F.data.startswith("pay:stars:"))
async def cb_pay_stars(call: CallbackQuery, user: User, settings: Settings) -> None:
    assert call.data is not None
    code = call.data.split(":", 2)[2]
    tariff = settings.tariff_by_code(code)
    if tariff is None:
        await call.answer("Tariff not found", show_alert=True)
        return
    lang = user.language
    title = translate(lang, "stars_invoice_title", title=tariff.title)
    desc = translate(
        lang,
        "stars_invoice_desc",
        days=tariff.days,
        messages=tariff.messages,
        images=tariff.images,
        voices=tariff.voices,
    )
    await call.answer()
    await call.message.answer_invoice(
        title=title[:32],
        description=desc[:255],
        payload=f"stars:{tariff.code}:{user.telegram_id}",
        provider_token="",  # Пустой для Stars
        currency="XTR",
        prices=[LabeledPrice(label=tariff.title, amount=tariff.price_stars)],
    )


@router.callback_query(F.data.startswith("pay:yookassa:"))
async def cb_pay_yookassa(
    call: CallbackQuery,
    user: User,
    settings: Settings,
    yookassa: YooKassaService,
) -> None:
    assert call.data is not None
    code = call.data.split(":", 2)[2]
    tariff = settings.tariff_by_code(code)
    if tariff is None:
        await call.answer("Tariff not found", show_alert=True)
        return
    lang = user.language
    if not yookassa.enabled:
        await call.answer(translate(lang, "pay_yookassa_disabled"), show_alert=True)
        return

    try:
        created = await yookassa.create_payment(tariff=tariff, user_tg_id=user.telegram_id)
    except Exception as exc:
        logger.exception("yookassa_create_error", error=str(exc))
        await call.answer("YooKassa error: " + str(exc)[:80], show_alert=True)
        return

    async with SessionLocal() as session:
        db_user = await repo.get_user_by_id(session, user.id)
        if db_user is None:
            return
        await repo.create_payment(
            session,
            db_user,
            provider="yookassa",
            tariff_code=tariff.code,
            amount=tariff.price_rub,
            currency=settings.yookassa_currency,
            external_id=created.id,
        )
        await session.commit()

    await call.answer()
    await call.message.edit_text(
        translate(lang, "pay_yookassa_created"),
        reply_markup=yookassa_check_keyboard(lang, created.confirmation_url, created.id),
    )


@router.callback_query(F.data.startswith("pay:check:"))
async def cb_pay_check(
    call: CallbackQuery,
    user: User,
    settings: Settings,
    yookassa: YooKassaService,
) -> None:
    assert call.data is not None
    payment_id = call.data.split(":", 2)[2]
    lang = user.language
    try:
        status = await yookassa.fetch_status(payment_id)
    except Exception as exc:
        logger.exception("yookassa_fetch_error", error=str(exc))
        await call.answer("YooKassa error", show_alert=True)
        return

    if status != "succeeded":
        if status in ("canceled",):
            await call.answer(translate(lang, "pay_canceled"), show_alert=True)
        else:
            await call.answer(translate(lang, "pay_not_found"), show_alert=True)
        return

    async with SessionLocal() as session:
        payment = await repo.get_payment_by_external_id(session, payment_id)
        if payment is None:
            await call.answer(translate(lang, "pay_not_found"), show_alert=True)
            return
        if payment.status == "succeeded":
            await call.answer(translate(lang, "pay_success", tariff=payment.tariff_code, until="—"), show_alert=True)
            return
        tariff = settings.tariff_by_code(payment.tariff_code)
        if tariff is None:
            await call.answer("Tariff missing", show_alert=True)
            return
        db_user = await repo.get_user_by_id(session, payment.user_id)
        if db_user is None:
            await call.answer("User missing", show_alert=True)
            return
        await repo.grant_subscription(
            session,
            db_user,
            tariff_code=tariff.code,
            days=tariff.days,
            messages=tariff.messages,
            images=tariff.images,
            voices=tariff.voices,
        )
        payment.status = "succeeded"
        await session.commit()
        exp = db_user.subscription_expires_at
        if exp and exp.tzinfo is None:
            exp = exp.replace(tzinfo=UTC)
        until = exp.strftime("%Y-%m-%d") if exp else "-"

    await call.answer()
    await call.message.edit_text(
        translate(lang, "pay_success", tariff=tariff.title, until=until),
        reply_markup=back_button(lang),
    )


# ==== Telegram Stars payments lifecycle ====


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def on_successful_payment(
    message: Message, user: User, settings: Settings
) -> None:
    sp = message.successful_payment
    assert sp is not None
    payload = sp.invoice_payload or ""
    parts = payload.split(":")
    if len(parts) < 3 or parts[0] != "stars":
        return
    tariff_code = parts[1]
    tariff = settings.tariff_by_code(tariff_code)
    if tariff is None:
        return

    async with SessionLocal() as session:
        db_user = await repo.get_user_by_id(session, user.id)
        if db_user is None:
            return
        await repo.create_payment(
            session,
            db_user,
            provider="stars",
            tariff_code=tariff.code,
            amount=tariff.price_stars,
            currency=sp.currency,
            external_id=sp.telegram_payment_charge_id,
        )
        # пометим как успешный сразу
        p = await repo.get_payment_by_external_id(session, sp.telegram_payment_charge_id)
        if p is not None:
            p.status = "succeeded"
        await repo.grant_subscription(
            session,
            db_user,
            tariff_code=tariff.code,
            days=tariff.days,
            messages=tariff.messages,
            images=tariff.images,
            voices=tariff.voices,
        )
        await session.commit()
        exp = db_user.subscription_expires_at
        if exp and exp.tzinfo is None:
            exp = exp.replace(tzinfo=UTC)
        until = exp.strftime("%Y-%m-%d") if exp else "-"

    await message.answer(
        translate(user.language, "pay_success", tariff=tariff.title, until=until)
    )
