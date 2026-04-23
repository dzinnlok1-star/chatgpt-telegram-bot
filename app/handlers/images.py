"""Image generation via /image and menu button."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message

from app.config import Settings
from app.db import repositories as repo
from app.db.models import User
from app.db.session import SessionLocal
from app.handlers.menu import MenuStates
from app.i18n import translate
from app.keyboards.inline import main_menu
from app.logger import get_logger
from app.services import limits as lim
from app.services.openai_service import OpenAIService

router = Router(name="images")
logger = get_logger("images")


@router.message(Command("image"))
async def cmd_image(message: Message, user: User, state: FSMContext) -> None:
    await state.set_state(MenuStates.awaiting_image_prompt)
    await message.answer(translate(user.language, "image_prompt"))


@router.message(MenuStates.awaiting_image_prompt, F.text)
async def on_image_prompt(
    message: Message,
    user: User,
    settings: Settings,
    openai: OpenAIService,
    state: FSMContext,
) -> None:
    lang = user.language
    prompt = (message.text or "").strip()
    if len(prompt) < 5:
        await message.answer(translate(lang, "image_too_short"))
        return

    async with SessionLocal() as session:
        db_user = await repo.get_user_by_id(session, user.id)
        if db_user is None:
            return
        if not lim.can_use(settings, db_user, lim.Resource.IMAGE):
            await session.commit()
            await message.answer(
                translate(lang, "limit_reached_images"),
                reply_markup=main_menu(lang),
            )
            await state.clear()
            return
        lim.consume(settings, db_user, lim.Resource.IMAGE)
        await session.commit()

    await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_PHOTO)
    status = await message.answer(translate(lang, "drawing"))
    try:
        img_bytes = await openai.generate_image(prompt=prompt)
    except Exception as exc:
        logger.exception("image_error", error=str(exc))
        await status.edit_text(translate(lang, "openai_error", error=str(exc)[:200]))
        await state.clear()
        return

    await status.delete()
    await message.answer_photo(
        BufferedInputFile(img_bytes, filename="image.png"),
        caption=translate(lang, "image_generated", prompt=prompt[:300]),
    )
    await state.clear()
