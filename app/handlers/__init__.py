"""Routers registration."""

from __future__ import annotations

from aiogram import Dispatcher

from app.handlers import admin, billing, chat, common, images, menu, voice


def register_handlers(dp: Dispatcher) -> None:
    # Порядок важен: сначала команды/меню, потом универсальные обработчики текста.
    dp.include_router(common.router)
    dp.include_router(menu.router)
    dp.include_router(billing.router)
    dp.include_router(admin.router)
    dp.include_router(images.router)
    dp.include_router(voice.router)
    dp.include_router(chat.router)
