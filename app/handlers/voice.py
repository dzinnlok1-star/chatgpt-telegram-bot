"""Voice message handler: transcribe + answer."""

from __future__ import annotations

import tempfile
from pathlib import Path

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.types import Message

from app.config import Settings
from app.db import repositories as repo
from app.db.models import User
from app.db.session import SessionLocal
from app.handlers.chat import _chunk_text
from app.i18n import translate
from app.keyboards.inline import main_menu
from app.logger import get_logger
from app.services import limits as lim
from app.services.chat_service import handle_user_message
from app.services.openai_service import OpenAIService

router = Router(name="voice")
logger = get_logger("voice")


@router.message(F.voice | F.audio)
async def on_voice(
    message: Message,
    user: User,
    settings: Settings,
    openai: OpenAIService,
) -> None:
    lang = user.language
    if user.is_blocked:
        await message.answer(translate(lang, "blocked"))
        return

    voice = message.voice or message.audio
    if voice is None:
        return

    # Лимит голосовых
    async with SessionLocal() as session:
        db_user = await repo.get_user_by_id(session, user.id)
        if db_user is None:
            return
        if not lim.can_use(settings, db_user, lim.Resource.VOICE):
            await session.commit()
            await message.answer(
                translate(lang, "limit_reached_voices"),
                reply_markup=main_menu(lang),
            )
            return
        lim.consume(settings, db_user, lim.Resource.VOICE)
        await session.commit()

    status = await message.answer(translate(lang, "transcribing"))
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    tmp_path: str | None = None
    try:
        file = await message.bot.get_file(voice.file_id)
        suffix = ".ogg" if message.voice else ".mp3"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
        await message.bot.download_file(file.file_path, destination=tmp_path)
        text = await openai.transcribe(file_path=tmp_path)
    except Exception as exc:
        logger.exception("voice_error", error=str(exc))
        await status.edit_text(translate(lang, "openai_error", error=str(exc)[:200]))
        return
    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass

    if not text:
        await status.edit_text(translate(lang, "openai_error", error="empty transcription"))
        return

    await status.edit_text(translate(lang, "voice_result", text=text[:2000]))

    # Теперь отвечаем моделью, как на обычное текстовое сообщение.
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
        try:
            reply = await handle_user_message(session, openai, settings, db_user, text)
        except Exception as exc:
            logger.exception("voice_chat_error", error=str(exc))
            await session.rollback()
            await message.answer(
                translate(lang, "openai_error", error=str(exc)[:200])
            )
            return
        lim.consume(settings, db_user, lim.Resource.MESSAGE)
        await session.commit()

    for chunk in _chunk_text(reply, 4000):
        await message.answer(chunk)
