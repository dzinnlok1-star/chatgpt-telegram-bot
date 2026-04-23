"""Wrapper around the OpenAI Python SDK."""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from typing import Any

import tiktoken
from openai import AsyncOpenAI, OpenAIError
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import Settings
from app.logger import get_logger

logger = get_logger("openai")


@dataclass
class ChatReply:
    text: str
    prompt_tokens: int
    completion_tokens: int


class OpenAIService:
    """Тонкая обёртка над AsyncOpenAI клиентом."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url or None,
        )

    async def close(self) -> None:
        await self._client.close()

    async def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
    ) -> ChatReply:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(min=1, max=8),
            retry=retry_if_exception_type(OpenAIError),
            reraise=True,
        ):
            with attempt:
                response = await self._client.chat.completions.create(
                    model=model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=temperature,
                )
        choice = response.choices[0]
        usage = response.usage
        text = choice.message.content or ""
        return ChatReply(
            text=text.strip(),
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
        )

    async def generate_image(
        self,
        *,
        prompt: str,
        size: str = "1024x1024",
        model: str | None = None,
    ) -> bytes:
        """Сгенерировать одно изображение и вернуть его как bytes (PNG)."""
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(2),
            wait=wait_exponential(min=1, max=6),
            retry=retry_if_exception_type(OpenAIError),
            reraise=True,
        ):
            with attempt:
                response = await self._client.images.generate(
                    model=model or self._settings.default_image_model,
                    prompt=prompt,
                    size=size,  # type: ignore[arg-type]
                    n=1,
                    response_format="b64_json",
                )
        b64 = response.data[0].b64_json
        if not b64:
            raise RuntimeError("OpenAI returned empty image data")
        return base64.b64decode(b64)

    async def transcribe(
        self,
        *,
        file_path: str,
        model: str | None = None,
    ) -> str:
        def _read() -> Any:
            return open(file_path, "rb")

        f = await asyncio.to_thread(_read)
        try:
            result = await self._client.audio.transcriptions.create(
                model=model or self._settings.default_transcribe_model,
                file=f,
            )
        finally:
            f.close()
        return (result.text or "").strip()


def count_tokens(text: str, model: str) -> int:
    """Грубая оценка токенов (нужна для триминга контекста)."""
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text or ""))
