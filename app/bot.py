"""Application bootstrap: bot, dispatcher, services wiring."""

from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from aiohttp import web

from app.config import Settings, get_settings
from app.db.session import init_models
from app.handlers import register_handlers
from app.logger import get_logger, setup_logging
from app.middlewares.user import UserMiddleware
from app.services.openai_service import OpenAIService
from app.services.yookassa_service import YooKassaService
from app.webhook import build_app

logger = get_logger("bot")


COMMANDS = [
    BotCommand(command="start", description="Начать работу / приветствие"),
    BotCommand(command="menu", description="Главное меню"),
    BotCommand(command="help", description="Справка"),
    BotCommand(command="new", description="Очистить контекст"),
    BotCommand(command="role", description="Выбрать роль ассистента"),
    BotCommand(command="model", description="Выбрать модель GPT"),
    BotCommand(command="image", description="Сгенерировать картинку"),
    BotCommand(command="profile", description="Мой профиль"),
    BotCommand(command="buy", description="Купить подписку"),
    BotCommand(command="ref", description="Реферальная программа"),
    BotCommand(command="lang", description="Сменить язык"),
]


async def _on_startup(bot: Bot) -> None:
    await init_models()
    await bot.set_my_commands(COMMANDS)
    me = await bot.get_me()
    logger.info("bot_started", username=me.username, id=me.id)


async def _run_webhook_server(settings: Settings, bot: Bot) -> None:
    app = build_app(settings, bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=settings.webhook_port)
    await site.start()
    logger.info("webhook_started", host="0.0.0.0", port=settings.webhook_port)
    # Держим сервер запущенным до остановки процесса.
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await runner.cleanup()


async def run() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info("starting_up")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher(storage=MemoryStorage())

    openai = OpenAIService(settings)
    yookassa = YooKassaService(settings)

    dispatcher["settings"] = settings
    dispatcher["openai"] = openai
    dispatcher["yookassa"] = yookassa

    # Middlewares
    user_mw = UserMiddleware(settings)
    dispatcher.message.middleware(user_mw)
    dispatcher.callback_query.middleware(user_mw)
    dispatcher.pre_checkout_query.middleware(user_mw)

    register_handlers(dispatcher)
    dispatcher.startup.register(_on_startup)

    tasks: list[asyncio.Task] = []
    if settings.webhook_enabled:
        tasks.append(asyncio.create_task(_run_webhook_server(settings, bot)))

    try:
        await dispatcher.start_polling(
            bot,
            settings=settings,
            openai=openai,
            yookassa=yookassa,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
    finally:
        for t in tasks:
            t.cancel()
        await openai.close()
        await bot.session.close()
        logger.info("stopped")
