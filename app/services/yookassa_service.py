"""YooKassa integration (creating + polling payments)."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass

from yookassa import Configuration
from yookassa import Payment as YooPayment

from app.config import Settings, Tariff
from app.logger import get_logger

logger = get_logger("yookassa")


@dataclass
class YooCreatedPayment:
    id: str
    confirmation_url: str


class YooKassaService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        if settings.yookassa_enabled:
            Configuration.account_id = settings.yookassa_shop_id
            Configuration.secret_key = settings.yookassa_secret_key

    @property
    def enabled(self) -> bool:
        return self._settings.yookassa_enabled

    async def create_payment(
        self,
        *,
        tariff: Tariff,
        user_tg_id: int,
        idempotency_key: str | None = None,
    ) -> YooCreatedPayment:
        if not self.enabled:
            raise RuntimeError("YooKassa is not configured")

        idem = idempotency_key or str(uuid.uuid4())
        payload = {
            "amount": {
                "value": f"{tariff.price_rub:.2f}",
                "currency": self._settings.yookassa_currency,
            },
            "confirmation": {
                "type": "redirect",
                "return_url": self._settings.yookassa_return_url,
            },
            "capture": True,
            "description": f"Подписка «{tariff.title}» · tg_id={user_tg_id}",
            "metadata": {
                "tariff_code": tariff.code,
                "user_tg_id": str(user_tg_id),
            },
        }

        payment = await asyncio.to_thread(YooPayment.create, payload, idem)
        return YooCreatedPayment(
            id=payment.id,
            confirmation_url=payment.confirmation.confirmation_url,
        )

    async def fetch_status(self, payment_id: str) -> str:
        payment = await asyncio.to_thread(YooPayment.find_one, payment_id)
        return payment.status
