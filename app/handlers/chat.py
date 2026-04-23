"""Free-text chat handler — default path for user messages."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.config import Settings
from app.db import repositories as repo
from app.db.models import User
from app.db.session import SessionLocal
from app.i18n import translate
from app.keyboards.inline import main_menu
from app.logger import get_logger
from app.services import limits as lim
from app.services.chat_service import handle_user_message
from app.services.openai_service import OpenAIService

router = Router(name="chat")
logger = get_logger("chat")


@router.message(F.text & ~F.text.startswith("/"))
async def on_text(
    message: Message,
    user: User,
    settings: Settings,
    openai: OpenAIService,
    state: FSMContext,
) -> None:
    lang = user.language
    if user.is_blocked:
        await message.answer(translate(lang, "blocked"))
        return

    # Проверка FSM-состояния — например, пользователь вводит prompt для картинки.
    current = await state.get_state()
    if current == "MenuStates:awaiting_image_prompt":
        # Пропускаем: обработает images.py
        return

    text = message.text.strip()
    if not text:
        return

    # Лимиты
    async with SessionLocal() as session:
        db_user = await repo.get_user_by_id(session, user.id)
        if db_user is None:
            return
        if not lim.can_use(settings, db_user, lim.Resource.MESSAGE):
            await session.commit()
            await message.answer(
                translate(lang, "limit_reached_messages"),
                reply_markup=main_menu(lang),
            )
            return

        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        try:
            reply = await handle_user_message(
                session, openai, settings, db_user, text
            )
        except Exception as exc:
            logger.exception("chat_error", error=str(exc))
            await session.rollback()
            await message.answer(translate(lang, "openai_error", error=str(exc)[:200]))
            return

        lim.consume(settings, db_user, lim.Resource.MESSAGE)
        await session.commit()

    # Телеграм ограничение на длину сообщения: 4096 символов.
    for chunk in _chunk_text(reply, 4000):
        await message.answer(chunk)


def _chunk_text(text: str, size: int) -> list[str]:
    if len(text) <= size:
        return [text]
    chunks: list[str] = []
    while text:
        chunks.append(text[:size])
        text = text[size:]
    return chunks
