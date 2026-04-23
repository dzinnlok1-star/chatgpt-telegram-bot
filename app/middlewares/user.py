"""Middleware that loads/creates User for every update."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update
from aiogram.types import User as TgUser

from app.config import Settings
from app.db import repositories as repo
from app.db.session import SessionLocal


def _tg_user_from(event: TelegramObject) -> TgUser | None:
    if isinstance(event, Update):
        for field in ("message", "edited_message", "callback_query", "pre_checkout_query"):
            val = getattr(event, field, None)
            if val is not None:
                user = getattr(val, "from_user", None)
                if user is not None:
                    return user
        return None
    if isinstance(event, (Message, CallbackQuery)):
        return event.from_user
    return getattr(event, "from_user", None)


class UserMiddleware(BaseMiddleware):
    """Загружает пользователя из БД, создаёт если нет, кладёт в data."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = _tg_user_from(event)
        if tg_user is None or tg_user.is_bot:
            return await handler(event, data)

        async with SessionLocal() as session:
            user, _ = await repo.get_or_create_user(
                session,
                telegram_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                language=self.settings.default_language,
                default_chat_model=self.settings.default_chat_model,
            )
            await session.commit()
            await session.refresh(user)

            data["user"] = user
            data["user_lang"] = user.language
            data["db_session_factory"] = SessionLocal
            return await handler(event, data)
