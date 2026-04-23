"""Application configuration loaded from environment / .env file."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass(frozen=True)
class Tariff:
    """Описывает один тариф подписки."""

    code: str
    title: str
    days: int
    messages: int
    images: int
    voices: int
    price_stars: int
    price_rub: int

    @property
    def price_rub_decimal(self) -> str:
        return f"{self.price_rub:.2f}"


def _parse_tariffs(raw: str) -> tuple[Tariff, ...]:
    tariffs: list[Tariff] = []
    for chunk in raw.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = chunk.split("|")
        if len(parts) != 8:
            raise ValueError(
                "Неверный формат TARIFFS. Ожидается "
                "КОД|НАЗВАНИЕ|ДНИ|СООБЩЕНИЯ|КАРТИНКИ|ГОЛОСА|ЗВЁЗДЫ|РУБ"
            )
        code, title, days, msgs, imgs, voices, stars, rub = parts
        tariffs.append(
            Tariff(
                code=code.strip(),
                title=title.strip(),
                days=int(days),
                messages=int(msgs),
                images=int(imgs),
                voices=int(voices),
                price_stars=int(stars),
                price_rub=int(rub),
            )
        )
    return tuple(tariffs)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram
    bot_token: str = Field(alias="BOT_TOKEN")
    admin_ids: str = Field(default="", alias="ADMIN_IDS")

    # OpenAI
    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    default_chat_model: str = Field(default="gpt-4o-mini", alias="DEFAULT_CHAT_MODEL")
    default_image_model: str = Field(default="dall-e-3", alias="DEFAULT_IMAGE_MODEL")
    default_transcribe_model: str = Field(default="whisper-1", alias="DEFAULT_TRANSCRIBE_MODEL")

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/bot.db",
        alias="DATABASE_URL",
    )

    # Limits
    free_daily_messages: int = Field(default=10, alias="FREE_DAILY_MESSAGES")
    free_daily_images: int = Field(default=1, alias="FREE_DAILY_IMAGES")
    free_daily_voices: int = Field(default=3, alias="FREE_DAILY_VOICES")
    context_max_messages: int = Field(default=20, alias="CONTEXT_MAX_MESSAGES")
    context_max_tokens: int = Field(default=4000, alias="CONTEXT_MAX_TOKENS")

    # Referral
    referral_bonus_messages: int = Field(default=50, alias="REFERRAL_BONUS_MESSAGES")
    referral_bonus_images: int = Field(default=3, alias="REFERRAL_BONUS_IMAGES")

    # Tariffs
    tariffs_raw: str = Field(
        default=(
            "basic|Базовый|30|500|20|30|150|299;"
            "pro|Про|30|2000|100|200|400|799;"
            "unlimited|Безлимит|30|100000|500|1000|1000|1990"
        ),
        alias="TARIFFS",
    )

    # YooKassa
    yookassa_shop_id: str = Field(default="", alias="YOOKASSA_SHOP_ID")
    yookassa_secret_key: str = Field(default="", alias="YOOKASSA_SECRET_KEY")
    yookassa_return_url: str = Field(
        default="https://t.me/", alias="YOOKASSA_RETURN_URL"
    )
    yookassa_currency: str = Field(default="RUB", alias="YOOKASSA_CURRENCY")

    # Webhook server (for YooKassa notifications)
    webhook_host: str = Field(default="", alias="WEBHOOK_HOST")
    webhook_path: str = Field(default="/yookassa/webhook", alias="WEBHOOK_PATH")
    webhook_port: int = Field(default=8080, alias="WEBHOOK_PORT")

    # Misc
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    default_language: str = Field(default="ru", alias="DEFAULT_LANGUAGE")

    @field_validator("default_language")
    @classmethod
    def _validate_lang(cls, v: str) -> str:
        v = v.lower()
        if v not in {"ru", "en", "uk"}:
            raise ValueError("DEFAULT_LANGUAGE должен быть одним из: ru, en, uk")
        return v

    @property
    def admin_id_set(self) -> frozenset[int]:
        result: set[int] = set()
        for chunk in self.admin_ids.split(","):
            chunk = chunk.strip()
            if chunk:
                result.add(int(chunk))
        return frozenset(result)

    @property
    def tariffs(self) -> tuple[Tariff, ...]:
        return _parse_tariffs(self.tariffs_raw)

    def tariff_by_code(self, code: str) -> Tariff | None:
        for t in self.tariffs:
            if t.code == code:
                return t
        return None

    @property
    def yookassa_enabled(self) -> bool:
        return bool(self.yookassa_shop_id and self.yookassa_secret_key)

    @property
    def webhook_enabled(self) -> bool:
        return bool(self.webhook_host)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
