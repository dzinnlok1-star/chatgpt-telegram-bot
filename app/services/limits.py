"""Daily limits & subscription accounting."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from app.config import Settings
from app.db.models import User


class Resource(StrEnum):
    MESSAGE = "message"
    IMAGE = "image"
    VOICE = "voice"


def _reset_daily_if_needed(user: User) -> None:
    now = datetime.now(tz=UTC)
    last = user.last_daily_reset_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    if last.date() != now.date():
        user.daily_messages_used = 0
        user.daily_images_used = 0
        user.daily_voices_used = 0
        user.last_daily_reset_at = now


def has_active_subscription(user: User) -> bool:
    if not user.subscription_expires_at:
        return False
    exp = user.subscription_expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=UTC)
    return exp > datetime.now(tz=UTC)


def _sub_left(user: User, resource: Resource) -> int:
    if not has_active_subscription(user):
        return 0
    if resource is Resource.MESSAGE:
        return user.subscription_messages_left
    if resource is Resource.IMAGE:
        return user.subscription_images_left
    return user.subscription_voices_left


def _free_limit(settings: Settings, resource: Resource) -> int:
    if resource is Resource.MESSAGE:
        return settings.free_daily_messages
    if resource is Resource.IMAGE:
        return settings.free_daily_images
    return settings.free_daily_voices


def _free_used(user: User, resource: Resource) -> int:
    if resource is Resource.MESSAGE:
        return user.daily_messages_used
    if resource is Resource.IMAGE:
        return user.daily_images_used
    return user.daily_voices_used


def _bonus_left(user: User, resource: Resource) -> int:
    if resource is Resource.MESSAGE:
        return user.bonus_messages
    if resource is Resource.IMAGE:
        return user.bonus_images
    return 0  # голосовые бонусов не имеют


def can_use(settings: Settings, user: User, resource: Resource) -> bool:
    _reset_daily_if_needed(user)
    if _sub_left(user, resource) > 0:
        return True
    if _bonus_left(user, resource) > 0:
        return True
    return _free_used(user, resource) < _free_limit(settings, resource)


def consume(settings: Settings, user: User, resource: Resource) -> None:
    """Списать 1 единицу ресурса по приоритету: подписка → бонусы → бесплатный лимит."""
    _reset_daily_if_needed(user)
    if _sub_left(user, resource) > 0:
        if resource is Resource.MESSAGE:
            user.subscription_messages_left -= 1
        elif resource is Resource.IMAGE:
            user.subscription_images_left -= 1
        else:
            user.subscription_voices_left -= 1
        return
    if _bonus_left(user, resource) > 0:
        if resource is Resource.MESSAGE:
            user.bonus_messages -= 1
        elif resource is Resource.IMAGE:
            user.bonus_images -= 1
        return
    if resource is Resource.MESSAGE:
        user.daily_messages_used += 1
    elif resource is Resource.IMAGE:
        user.daily_images_used += 1
    else:
        user.daily_voices_used += 1


def free_limits(settings: Settings) -> tuple[int, int, int]:
    return (
        settings.free_daily_messages,
        settings.free_daily_images,
        settings.free_daily_voices,
    )
