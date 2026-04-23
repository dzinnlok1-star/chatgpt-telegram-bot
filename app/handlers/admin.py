"""Admin panel: stats, broadcast, grant/block."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.config import Settings
from app.db import repositories as repo
from app.db.models import User
from app.db.session import SessionLocal
from app.i18n import translate
from app.keyboards.inline import admin_menu_keyboard
from app.logger import get_logger

router = Router(name="admin")
logger = get_logger("admin")


class AdminStates(StatesGroup):
    waiting_broadcast = State()
    waiting_confirm = State()


def _is_admin(user: User, settings: Settings) -> bool:
    return user.telegram_id in settings.admin_id_set


@router.message(Command("admin"))
async def cmd_admin(message: Message, user: User, settings: Settings) -> None:
    if not _is_admin(user, settings):
        await message.answer(translate(user.language, "admin_only"))
        return
    await message.answer(
        translate(user.language, "admin_panel"),
        reply_markup=admin_menu_keyboard(),
    )


@router.callback_query(F.data == "admin:stats")
async def cb_stats(call: CallbackQuery, user: User, settings: Settings) -> None:
    if not _is_admin(user, settings):
        await call.answer(translate(user.language, "admin_only"), show_alert=True)
        return
    now = datetime.now(tz=UTC)
    async with SessionLocal() as session:
        total = await repo.count_users(session)
        active_24h = await repo.count_active_users(session, now - timedelta(days=1))
        active_7d = await repo.count_active_users(session, now - timedelta(days=7))
        premium = await repo.count_premium_users(session)
        stars_rev = await repo.sum_revenue(session, "XTR")
        rub_rev = await repo.sum_revenue(session, settings.yookassa_currency)
    await call.answer()
    await call.message.edit_text(
        translate(
            user.language,
            "admin_stats",
            total=total,
            active_24h=active_24h,
            active_7d=active_7d,
            premium=premium,
            stars=stars_rev,
            rub=rub_rev,
        ),
        reply_markup=admin_menu_keyboard(),
    )


@router.callback_query(F.data == "admin:broadcast")
async def cb_broadcast(
    call: CallbackQuery, user: User, settings: Settings, state: FSMContext
) -> None:
    if not _is_admin(user, settings):
        await call.answer(translate(user.language, "admin_only"), show_alert=True)
        return
    await call.answer()
    await state.set_state(AdminStates.waiting_broadcast)
    await call.message.answer(translate(user.language, "admin_broadcast_prompt"))


@router.message(AdminStates.waiting_broadcast, F.text == "/cancel")
async def cancel_broadcast(message: Message, user: User, state: FSMContext) -> None:
    await state.clear()
    await message.answer(translate(user.language, "canceled"))


@router.message(AdminStates.waiting_broadcast)
async def on_broadcast_text(
    message: Message, user: User, settings: Settings, state: FSMContext
) -> None:
    if not _is_admin(user, settings):
        await state.clear()
        return
    async with SessionLocal() as session:
        ids = await repo.iter_all_telegram_ids(session)
    await state.update_data(broadcast_text=message.html_text, targets=ids)
    await state.set_state(AdminStates.waiting_confirm)
    await message.answer(
        translate(user.language, "admin_broadcast_confirm", count=len(ids))
    )


@router.message(AdminStates.waiting_confirm, F.text == "/cancel")
async def cancel_confirm(message: Message, user: User, state: FSMContext) -> None:
    await state.clear()
    await message.answer(translate(user.language, "canceled"))


@router.message(AdminStates.waiting_confirm, F.text == "/confirm")
async def on_confirm(message: Message, user: User, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    text = data.get("broadcast_text", "")
    targets: list[int] = data.get("targets", [])
    ok = 0
    fail = 0
    for tg_id in targets:
        try:
            await message.bot.send_message(tg_id, text)
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)  # ~20 msg/sec, с запасом под Telegram ограничения
    await message.answer(
        translate(user.language, "admin_broadcast_sent", ok=ok, fail=fail)
    )


@router.message(Command("grant"))
async def cmd_grant(
    message: Message,
    user: User,
    settings: Settings,
    command: CommandObject,
) -> None:
    if not _is_admin(user, settings):
        await message.answer(translate(user.language, "admin_only"))
        return
    args = (command.args or "").split()
    if len(args) != 2:
        await message.answer(translate(user.language, "admin_grant_usage"))
        return
    try:
        tg_id = int(args[0])
    except ValueError:
        await message.answer(translate(user.language, "admin_grant_usage"))
        return
    code = args[1]
    tariff = settings.tariff_by_code(code)
    if tariff is None:
        await message.answer(
            translate(user.language, "admin_grant_bad_tariff", code=code)
        )
        return
    async with SessionLocal() as session:
        target = await repo.get_user_by_telegram_id(session, tg_id)
        if target is None:
            await message.answer(translate(user.language, "admin_grant_no_user"))
            return
        await repo.grant_subscription(
            session,
            target,
            tariff_code=tariff.code,
            days=tariff.days,
            messages=tariff.messages,
            images=tariff.images,
            voices=tariff.voices,
        )
        await session.commit()
    await message.answer(
        translate(user.language, "admin_grant_ok", tariff=tariff.title, tg_id=tg_id)
    )


@router.message(Command("block"))
async def cmd_block(
    message: Message,
    user: User,
    settings: Settings,
    command: CommandObject,
) -> None:
    if not _is_admin(user, settings):
        await message.answer(translate(user.language, "admin_only"))
        return
    if not command.args:
        await message.answer(translate(user.language, "admin_block_usage"))
        return
    try:
        tg_id = int(command.args.strip())
    except ValueError:
        await message.answer(translate(user.language, "admin_block_usage"))
        return
    async with SessionLocal() as session:
        ok = await repo.set_blocked(session, tg_id, True)
        await session.commit()
    if not ok:
        await message.answer(translate(user.language, "admin_grant_no_user"))
        return
    await message.answer(translate(user.language, "admin_block_ok", tg_id=tg_id))


@router.message(Command("unblock"))
async def cmd_unblock(
    message: Message,
    user: User,
    settings: Settings,
    command: CommandObject,
) -> None:
    if not _is_admin(user, settings):
        await message.answer(translate(user.language, "admin_only"))
        return
    if not command.args:
        await message.answer(translate(user.language, "admin_block_usage"))
        return
    try:
        tg_id = int(command.args.strip())
    except ValueError:
        await message.answer(translate(user.language, "admin_block_usage"))
        return
    async with SessionLocal() as session:
        ok = await repo.set_blocked(session, tg_id, False)
        await session.commit()
    if not ok:
        await message.answer(translate(user.language, "admin_grant_no_user"))
        return
    await message.answer(translate(user.language, "admin_unblock_ok", tg_id=tg_id))
