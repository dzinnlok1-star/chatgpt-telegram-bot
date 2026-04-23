"""Common commands: /start, /help, /lang, /new, /profile."""

from __future__ import annotations

from datetime import UTC

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message

from app.config import Settings
from app.db import repositories as repo
from app.db.models import User
from app.db.session import SessionLocal
from app.i18n import translate
from app.keyboards.inline import (
    languages_keyboard,
    main_menu,
    models_keyboard,
    roles_keyboard,
)
from app.services import limits as lim
from app.services.roles import get_role

router = Router(name="common")


def _fmt_sub(user: User, lang: str) -> str:
    if not lim.has_active_subscription(user) or not user.subscription_expires_at:
        return translate(lang, "sub_inactive")
    exp = user.subscription_expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=UTC)
    return translate(
        lang,
        "sub_active",
        tariff=user.subscription_tariff or "",
        until=exp.strftime("%Y-%m-%d"),
        m=user.subscription_messages_left,
        i=user.subscription_images_left,
        v=user.subscription_voices_left,
    )


def _profile_text(user: User, settings: Settings) -> str:
    lang = user.language
    m_lim, i_lim, v_lim = lim.free_limits(settings)
    role_title = translate(lang, get_role(user.role_code).i18n_key)
    return translate(
        lang,
        "profile",
        tg_id=user.telegram_id,
        lang=lang.upper(),
        role=role_title,
        model=user.chat_model,
        m_used=user.daily_messages_used,
        m_limit=m_lim,
        i_used=user.daily_images_used,
        i_limit=i_lim,
        v_used=user.daily_voices_used,
        v_limit=v_lim,
        bonus_m=user.bonus_messages,
        bonus_i=user.bonus_images,
        sub_status=_fmt_sub(user, lang),
    )


@router.message(CommandStart(deep_link=True))
async def cmd_start_with_deeplink(
    message: Message,
    command: CommandObject,
    user: User,
    settings: Settings,
) -> None:
    await _start_flow(message, user, settings, command.args)


@router.message(CommandStart())
async def cmd_start(message: Message, user: User, settings: Settings) -> None:
    await _start_flow(message, user, settings, None)


async def _start_flow(
    message: Message,
    user: User,
    settings: Settings,
    payload: str | None,
) -> None:
    lang = user.language
    got_referral_bonus = False

    if payload and payload.startswith("ref"):
        try:
            referrer_tg_id = int(payload[3:])
        except ValueError:
            referrer_tg_id = 0
        if referrer_tg_id and referrer_tg_id != user.telegram_id and user.referrer_id is None:
            async with SessionLocal() as session:
                referrer = await repo.get_user_by_telegram_id(session, referrer_tg_id)
                target = await repo.get_user_by_telegram_id(session, user.telegram_id)
                if referrer and target and target.referrer_id is None:
                    target.referrer_id = referrer.id
                    target.bonus_messages += settings.referral_bonus_messages
                    target.bonus_images += settings.referral_bonus_images
                    referrer.bonus_messages += settings.referral_bonus_messages
                    referrer.bonus_images += settings.referral_bonus_images
                    referrer.referrals_count += 1
                    await session.commit()
                    got_referral_bonus = True
                    # Уведомим пригласителя.
                    try:
                        await message.bot.send_message(
                            referrer.telegram_id,
                            translate(
                                referrer.language,
                                "referral_reward",
                                bonus_m=settings.referral_bonus_messages,
                                bonus_i=settings.referral_bonus_images,
                            ),
                        )
                    except Exception:
                        pass

    name = message.from_user.first_name or message.from_user.full_name or "друг"
    text = translate(
        lang,
        "welcome",
        name=name,
        messages=settings.free_daily_messages,
        images=settings.free_daily_images,
        voices=settings.free_daily_voices,
    )
    if got_referral_bonus:
        text += "\n\n" + translate(
            lang,
            "welcome_bonus",
            messages=settings.referral_bonus_messages,
            images=settings.referral_bonus_images,
        )

    await message.answer(text, reply_markup=main_menu(lang))


@router.message(Command("help"))
async def cmd_help(message: Message, user: User) -> None:
    await message.answer(translate(user.language, "help"))


@router.message(Command("menu"))
async def cmd_menu(message: Message, user: User) -> None:
    await message.answer(
        translate(user.language, "menu_title"), reply_markup=main_menu(user.language)
    )


@router.message(Command("profile"))
async def cmd_profile(message: Message, user: User, settings: Settings) -> None:
    await message.answer(_profile_text(user, settings))


@router.message(Command("lang"))
async def cmd_lang(message: Message, user: User) -> None:
    await message.answer(
        translate(user.language, "choose_language"),
        reply_markup=languages_keyboard(),
    )


@router.callback_query(F.data.startswith("lang:"))
async def cb_lang(call: CallbackQuery, user: User) -> None:
    assert call.data is not None
    code = call.data.split(":", 1)[1]
    async with SessionLocal() as session:
        db_user = await repo.get_user_by_id(session, user.id)
        if db_user is not None:
            db_user.language = code
            await session.commit()
    await call.answer()
    await call.message.edit_text(translate(code, "language_set"))
    await call.message.answer(
        translate(code, "menu_title"), reply_markup=main_menu(code)
    )


@router.message(Command("role"))
async def cmd_role(message: Message, user: User) -> None:
    await message.answer(
        translate(user.language, "choose_role"),
        reply_markup=roles_keyboard(user.language),
    )


@router.message(Command("model"))
async def cmd_model(message: Message, user: User) -> None:
    await message.answer(
        translate(user.language, "choose_model"),
        reply_markup=models_keyboard(user.language, user.chat_model),
    )


@router.message(Command("ref"))
async def cmd_ref(message: Message, user: User, settings: Settings) -> None:
    bot_user = await message.bot.get_me()
    link = f"https://t.me/{bot_user.username}?start=ref{user.telegram_id}"
    await message.answer(
        translate(
            user.language,
            "referral_info",
            bonus_m=settings.referral_bonus_messages,
            bonus_i=settings.referral_bonus_images,
            link=link,
            count=user.referrals_count,
        )
    )


@router.message(Command("new"))
async def cmd_new(message: Message, user: User) -> None:
    async with SessionLocal() as session:
        db_user = await repo.get_user_by_id(session, user.id)
        if db_user is None:
            return
        cleared = await repo.clear_context(session, db_user)
        await session.commit()
    key = "new_dialog" if cleared else "new_dialog_empty"
    await message.answer(translate(user.language, key))


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, user: User, state=None) -> None:
    if state is not None:
        await state.clear()
    await message.answer(translate(user.language, "canceled"))
