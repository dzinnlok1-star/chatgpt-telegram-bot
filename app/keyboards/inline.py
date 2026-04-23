"""Inline keyboards."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.config import Tariff
from app.i18n import language_title, supported_languages, translate
from app.services.roles import all_roles


def main_menu(lang: str) -> InlineKeyboardMarkup:
    t = lambda k: translate(lang, k)  # noqa: E731
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("btn_profile"), callback_data="menu:profile"),
                InlineKeyboardButton(text=t("btn_buy"), callback_data="menu:buy"),
            ],
            [
                InlineKeyboardButton(text=t("btn_ref"), callback_data="menu:ref"),
                InlineKeyboardButton(text=t("btn_role"), callback_data="menu:role"),
            ],
            [
                InlineKeyboardButton(text=t("btn_model"), callback_data="menu:model"),
                InlineKeyboardButton(text=t("btn_image"), callback_data="menu:image"),
            ],
            [
                InlineKeyboardButton(text=t("btn_new"), callback_data="menu:new"),
                InlineKeyboardButton(text=t("btn_lang"), callback_data="menu:lang"),
            ],
            [InlineKeyboardButton(text=t("btn_close"), callback_data="menu:close")],
        ]
    )


def back_button(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=translate(lang, "btn_back"), callback_data="menu:open")]
        ]
    )


def languages_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=language_title(code), callback_data=f"lang:{code}")]
        for code in supported_languages()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def roles_keyboard(lang: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=translate(lang, r.i18n_key),
                callback_data=f"role:{r.code}",
            )
        ]
        for r in all_roles()
    ]
    rows.append(
        [InlineKeyboardButton(text=translate(lang, "btn_back"), callback_data="menu:open")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


MODEL_CHOICES: tuple[str, ...] = (
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4.1-mini",
    "gpt-4.1",
    "o4-mini",
)


def models_keyboard(lang: str, current: str) -> InlineKeyboardMarkup:
    rows = []
    for model in MODEL_CHOICES:
        prefix = "✅ " if model == current else ""
        rows.append(
            [InlineKeyboardButton(text=f"{prefix}{model}", callback_data=f"model:{model}")]
        )
    rows.append(
        [InlineKeyboardButton(text=translate(lang, "btn_back"), callback_data="menu:open")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def tariffs_keyboard(lang: str, tariffs: tuple[Tariff, ...]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{t.title} · {t.price_stars}⭐ / {t.price_rub}₽",
                callback_data=f"buy:{t.code}",
            )
        ]
        for t in tariffs
    ]
    rows.append(
        [InlineKeyboardButton(text=translate(lang, "btn_back"), callback_data="menu:open")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pay_methods_keyboard(
    lang: str, tariff_code: str, *, yookassa_enabled: bool
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=translate(lang, "btn_pay_stars"),
                callback_data=f"pay:stars:{tariff_code}",
            )
        ]
    ]
    if yookassa_enabled:
        rows.append(
            [
                InlineKeyboardButton(
                    text=translate(lang, "btn_pay_yookassa"),
                    callback_data=f"pay:yookassa:{tariff_code}",
                )
            ]
        )
    rows.append(
        [InlineKeyboardButton(text=translate(lang, "btn_back"), callback_data="menu:buy")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def yookassa_check_keyboard(
    lang: str, confirmation_url: str, payment_id: str
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=translate(lang, "btn_open_invoice"),
                    url=confirmation_url,
                )
            ],
            [
                InlineKeyboardButton(
                    text=translate(lang, "btn_check_payment"),
                    callback_data=f"pay:check:{payment_id}",
                )
            ],
        ]
    )


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")],
            [InlineKeyboardButton(text="📣 Рассылка", callback_data="admin:broadcast")],
            [InlineKeyboardButton(text="✖️ Закрыть", callback_data="menu:close")],
        ]
    )
