"""Optional aiohttp webhook server for YooKassa notifications."""

from __future__ import annotations

from aiohttp import web

from app.config import Settings
from app.db import repositories as repo
from app.db.session import SessionLocal
from app.i18n import translate
from app.logger import get_logger

logger = get_logger("webhook")


async def _yookassa_handler(request: web.Request) -> web.Response:
    settings: Settings = request.app["settings"]
    bot = request.app["bot"]
    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text="bad json")

    event = data.get("event")
    obj = data.get("object") or {}
    payment_id = obj.get("id")
    status = obj.get("status")
    logger.info("yookassa_webhook", event=event, status=status, payment_id=payment_id)

    if event != "payment.succeeded" or not payment_id:
        return web.Response(status=200, text="ok")

    async with SessionLocal() as session:
        payment = await repo.get_payment_by_external_id(session, payment_id)
        if payment is None:
            logger.warning("payment_not_found", payment_id=payment_id)
            return web.Response(status=200, text="ok")
        if payment.status == "succeeded":
            return web.Response(status=200, text="ok")
        tariff = settings.tariff_by_code(payment.tariff_code)
        user = await repo.get_user_by_id(session, payment.user_id)
        if tariff is None or user is None:
            return web.Response(status=200, text="ok")
        await repo.grant_subscription(
            session,
            user,
            tariff_code=tariff.code,
            days=tariff.days,
            messages=tariff.messages,
            images=tariff.images,
            voices=tariff.voices,
        )
        payment.status = "succeeded"
        await session.commit()
        exp = user.subscription_expires_at
        until = exp.strftime("%Y-%m-%d") if exp else "-"
        try:
            await bot.send_message(
                user.telegram_id,
                translate(user.language, "pay_success", tariff=tariff.title, until=until),
            )
        except Exception as exc:
            logger.warning("notify_failed", error=str(exc))

    return web.Response(status=200, text="ok")


def build_app(settings: Settings, bot) -> web.Application:
    app = web.Application()
    app["settings"] = settings
    app["bot"] = bot
    app.router.add_post(settings.webhook_path, _yookassa_handler)
    app.router.add_get("/health", lambda _r: web.Response(text="ok"))
    return app
