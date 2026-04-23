"""High-level chat flow: build context, call OpenAI, persist messages."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db import repositories as repo
from app.db.models import User
from app.services.openai_service import OpenAIService, count_tokens
from app.services.roles import get_role


async def build_messages(
    session: AsyncSession,
    user: User,
    settings: Settings,
    user_input: str,
) -> list[dict[str, str]]:
    role = get_role(user.role_code)
    history = await repo.get_recent_context(session, user, settings.context_max_messages)

    messages: list[dict[str, str]] = [{"role": "system", "content": role.system_prompt}]
    token_budget = settings.context_max_tokens
    buffer: list[dict[str, str]] = []

    for m in reversed(history):
        tokens = m.tokens or count_tokens(m.content, user.chat_model)
        if tokens > token_budget:
            break
        token_budget -= tokens
        buffer.append({"role": m.role, "content": m.content})
    buffer.reverse()
    messages.extend(buffer)

    messages.append({"role": "user", "content": user_input})
    return messages


async def handle_user_message(
    session: AsyncSession,
    openai: OpenAIService,
    settings: Settings,
    user: User,
    text: str,
) -> str:
    """Основной путь: сохранить сообщение, спросить модель, сохранить ответ."""
    user_tokens = count_tokens(text, user.chat_model)
    await repo.add_chat_message(session, user, "user", text, tokens=user_tokens)

    messages = await build_messages(session, user, settings, "")
    # build_messages добавил пустое user-сообщение в конец — заменим его настоящим.
    messages[-1] = {"role": "user", "content": text}

    reply = await openai.chat(model=user.chat_model, messages=messages)
    await repo.add_chat_message(
        session, user, "assistant", reply.text, tokens=reply.completion_tokens
    )
    return reply.text
