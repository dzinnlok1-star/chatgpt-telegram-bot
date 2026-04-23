"""Database models."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


class User(Base):
    """Telegram-пользователь бота."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(128))
    last_name: Mapped[str | None] = mapped_column(String(128))
    language: Mapped[str] = mapped_column(String(5), default="ru")
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Выбор пользователя
    chat_model: Mapped[str] = mapped_column(String(64), default="gpt-4o-mini")
    role_code: Mapped[str] = mapped_column(String(32), default="default")

    # Лимиты / счётчики (сбрасываются раз в сутки)
    daily_messages_used: Mapped[int] = mapped_column(Integer, default=0)
    daily_images_used: Mapped[int] = mapped_column(Integer, default=0)
    daily_voices_used: Mapped[int] = mapped_column(Integer, default=0)
    last_daily_reset_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    # Бонусы и подписка
    bonus_messages: Mapped[int] = mapped_column(Integer, default=0)
    bonus_images: Mapped[int] = mapped_column(Integer, default=0)
    subscription_tariff: Mapped[str | None] = mapped_column(String(32))
    subscription_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    subscription_messages_left: Mapped[int] = mapped_column(Integer, default=0)
    subscription_images_left: Mapped[int] = mapped_column(Integer, default=0)
    subscription_voices_left: Mapped[int] = mapped_column(Integer, default=0)

    # Реферальная программа
    referrer_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL")
    )
    referrals_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    payments: Mapped[list[Payment]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    """Контекст переписки с моделью."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))  # system|user|assistant
    content: Mapped[str] = mapped_column(Text)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped[User] = relationship(back_populates="messages")


class Payment(Base):
    """Платёж пользователя (Telegram Stars или ЮKassa)."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(32))  # stars | yookassa
    tariff_code: Mapped[str] = mapped_column(String(32))
    amount: Mapped[int] = mapped_column(Integer)  # в целых единицах (звёзды или рубли)
    currency: Mapped[str] = mapped_column(String(8))  # XTR | RUB
    external_id: Mapped[str | None] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(24), default="pending")
    # pending | succeeded | canceled | failed

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    user: Mapped[User] = relationship(back_populates="payments")
