"""Data access helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChatMessage, Payment, User


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    *,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    language: str = "ru",
    referrer_telegram_id: int | None = None,
    default_chat_model: str = "gpt-4o-mini",
) -> tuple[User, bool]:
    """Возвращает (user, is_new)."""
    stmt = select(User).where(User.telegram_id == telegram_id)
    res = await session.execute(stmt)
    user = res.scalar_one_or_none()
    if user is not None:
        # Мягко обновим публичные поля, если изменились
        changed = False
        if username != user.username:
            user.username = username
            changed = True
        if first_name and first_name != user.first_name:
            user.first_name = first_name
            changed = True
        if last_name and last_name != user.last_name:
            user.last_name = last_name
            changed = True
        if changed:
            await session.flush()
        return user, False

    referrer = None
    if referrer_telegram_id and referrer_telegram_id != telegram_id:
        ref_stmt = select(User).where(User.telegram_id == referrer_telegram_id)
        referrer = (await session.execute(ref_stmt)).scalar_one_or_none()

    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        language=language,
        chat_model=default_chat_model,
        referrer_id=referrer.id if referrer else None,
    )
    session.add(user)
    await session.flush()
    return user, True


async def get_user_by_telegram_id(
    session: AsyncSession, telegram_id: int
) -> User | None:
    stmt = select(User).where(User.telegram_id == telegram_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def add_chat_message(
    session: AsyncSession,
    user: User,
    role: str,
    content: str,
    tokens: int = 0,
) -> ChatMessage:
    msg = ChatMessage(user_id=user.id, role=role, content=content, tokens=tokens)
    session.add(msg)
    await session.flush()
    return msg


async def get_recent_context(
    session: AsyncSession, user: User, limit: int
) -> list[ChatMessage]:
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.user_id == user.id)
        .order_by(desc(ChatMessage.id))
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return list(reversed(rows))


async def clear_context(session: AsyncSession, user: User) -> int:
    stmt = select(func.count(ChatMessage.id)).where(ChatMessage.user_id == user.id)
    total = (await session.execute(stmt)).scalar_one()
    await session.execute(
        ChatMessage.__table__.delete().where(ChatMessage.user_id == user.id)
    )
    return int(total)


async def create_payment(
    session: AsyncSession,
    user: User,
    *,
    provider: str,
    tariff_code: str,
    amount: int,
    currency: str,
    external_id: str | None = None,
) -> Payment:
    payment = Payment(
        user_id=user.id,
        provider=provider,
        tariff_code=tariff_code,
        amount=amount,
        currency=currency,
        external_id=external_id,
        status="pending",
    )
    session.add(payment)
    await session.flush()
    return payment


async def get_payment_by_external_id(
    session: AsyncSession, external_id: str
) -> Payment | None:
    stmt = select(Payment).where(Payment.external_id == external_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def count_users(session: AsyncSession) -> int:
    return int((await session.execute(select(func.count(User.id)))).scalar_one())


async def count_active_users(session: AsyncSession, since: datetime) -> int:
    stmt = (
        select(func.count(func.distinct(ChatMessage.user_id)))
        .where(ChatMessage.created_at >= since)
    )
    return int((await session.execute(stmt)).scalar_one())


async def count_premium_users(session: AsyncSession) -> int:
    now = datetime.now(tz=UTC)
    stmt = select(func.count(User.id)).where(
        User.subscription_expires_at.is_not(None),
        User.subscription_expires_at > now,
    )
    return int((await session.execute(stmt)).scalar_one())


async def sum_revenue(session: AsyncSession, currency: str) -> int:
    stmt = select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.status == "succeeded", Payment.currency == currency
    )
    return int((await session.execute(stmt)).scalar_one())


async def iter_all_telegram_ids(session: AsyncSession) -> list[int]:
    stmt = select(User.telegram_id).where(User.is_blocked.is_(False))
    return [row[0] for row in (await session.execute(stmt)).all()]


async def set_blocked(session: AsyncSession, telegram_id: int, blocked: bool) -> bool:
    user = await get_user_by_telegram_id(session, telegram_id)
    if user is None:
        return False
    user.is_blocked = blocked
    return True


async def grant_subscription(
    session: AsyncSession,
    user: User,
    *,
    tariff_code: str,
    days: int,
    messages: int,
    images: int,
    voices: int,
) -> None:
    now = datetime.now(tz=UTC)
    base = user.subscription_expires_at if (
        user.subscription_expires_at and user.subscription_expires_at > now
    ) else now
    user.subscription_tariff = tariff_code
    user.subscription_expires_at = base + timedelta(days=days)
    user.subscription_messages_left += messages
    user.subscription_images_left += images
    user.subscription_voices_left += voices
