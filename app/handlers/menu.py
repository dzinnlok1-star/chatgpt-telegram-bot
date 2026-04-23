"""Inline menu navigation."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery

from app.config import Settings
from app.db import repositories as repo
from app.db.models import User
from app.db.session import SessionLocal
from app.handlers.common import _profile_text  # reuse profile formatter
from app.i18n import translate
from app.keyboards.inline import (
    back_button,
    languages_keyboard,
    main_menu,
    models_keyboard,
    roles_keyboard,
    tariffs_keyboard,
)
from app.services.roles import get_role

router = Router(name="menu")


class MenuStates(StatesGroup):
    awaiting_image_prompt = State()


@router.callback_query(F.data == "menu:close")
async def cb_close(call: CallbackQuery) -> None:
    await call.answer()
    if call.message is not None:
        await call.message.delete()


@router.callback_query(F.data == "menu:open")
async def cb_open(call: CallbackQuery, user: User) -> None:
    await call.answer()
    await call.message.edit_text(
        translate(user.language, "menu_title"),
        reply_markup=main_menu(user.language),
    )


@router.callback_query(F.data == "menu:profile")
async def cb_profile(call: CallbackQuery, user: User, settings: Settings) -> None:
    await call.answer()
    await call.message.edit_text(
        _profile_text(user, settings),
        reply_markup=back_button(user.language),
    )


@router.callback_query(F.data == "menu:lang")
async def cb_lang(call: CallbackQuery, user: User) -> None:
    await call.answer()
    await call.message.edit_text(
        translate(user.language, "choose_language"),
        reply_markup=languages_keyboard(),
    )


@router.callback_query(F.data == "menu:role")
async def cb_role_menu(call: CallbackQuery, user: User) -> None:
    await call.answer()
    await call.message.edit_text(
        translate(user.language, "choose_role"),
        reply_markup=roles_keyboard(user.language),
    )


@router.callback_query(F.data.startswith("role:"))
async def cb_role_set(call: CallbackQuery, user: User) -> None:
    assert call.data is not None
    code = call.data.split(":", 1)[1]
    role = get_role(code)
    async with SessionLocal() as session:
        db_user = await repo.get_user_by_id(session, user.id)
        if db_user is not None:
            db_user.role_code = role.code
            await session.commit()
    await call.answer()
    title = translate(user.language, role.i18n_key)
    await call.message.edit_text(
        translate(user.language, "role_set", role=title),
        reply_markup=back_button(user.language),
    )


@router.callback_query(F.data == "menu:model")
async def cb_model_menu(call: CallbackQuery, user: User) -> None:
    await call.answer()
    await call.message.edit_text(
        translate(user.language, "choose_model"),
        reply_markup=models_keyboard(user.language, user.chat_model),
    )


@router.callback_query(F.data.startswith("model:"))
async def cb_model_set(call: CallbackQuery, user: User) -> None:
    assert call.data is not None
    model = call.data.split(":", 1)[1]
    async with SessionLocal() as session:
        db_user = await repo.get_user_by_id(session, user.id)
        if db_user is not None:
            db_user.chat_model = model
            await session.commit()
    await call.answer()
    await call.message.edit_text(
        translate(user.language, "model_set", model=model),
        reply_markup=back_button(user.language),
    )


@router.callback_query(F.data == "menu:new")
async def cb_new(call: CallbackQuery, user: User) -> None:
    async with SessionLocal() as session:
        db_user = await repo.get_user_by_id(session, user.id)
        cleared = await repo.clear_context(session, db_user) if db_user else 0
        await session.commit()
    key = "new_dialog" if cleared else "new_dialog_empty"
    await call.answer(translate(user.language, key), show_alert=False)


@router.callback_query(F.data == "menu:buy")
async def cb_buy(call: CallbackQuery, user: User, settings: Settings) -> None:
    await call.answer()
    await call.message.edit_text(
        translate(user.language, "buy_title"),
        reply_markup=tariffs_keyboard(user.language, settings.tariffs),
    )


@router.callback_query(F.data == "menu:ref")
async def cb_ref(call: CallbackQuery, user: User, settings: Settings) -> None:
    await call.answer()
    bot_user = await call.bot.get_me()
    link = f"https://t.me/{bot_user.username}?start=ref{user.telegram_id}"
    await call.message.edit_text(
        translate(
            user.language,
            "referral_info",
            bonus_m=settings.referral_bonus_messages,
            bonus_i=settings.referral_bonus_images,
            link=link,
            count=user.referrals_count,
        ),
        reply_markup=back_button(user.language),
    )


@router.callback_query(F.data == "menu:image")
async def cb_image(call: CallbackQuery, user: User, state: FSMContext) -> None:
    await call.answer()
    await state.set_state(MenuStates.awaiting_image_prompt)
    await call.message.edit_text(
        translate(user.language, "image_prompt"),
        reply_markup=back_button(user.language),
    )



