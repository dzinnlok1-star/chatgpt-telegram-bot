"""Simple JSON-based i18n."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_LOCALES_DIR = Path(__file__).parent / "locales"
_SUPPORTED: tuple[str, ...] = ("ru", "en", "uk")


@lru_cache
def _load(lang: str) -> dict[str, str]:
    path = _LOCALES_DIR / f"{lang}.json"
    if not path.exists():
        path = _LOCALES_DIR / "ru.json"
    return json.loads(path.read_text(encoding="utf-8"))


def translate(lang: str, key: str, **kwargs: object) -> str:
    if lang not in _SUPPORTED:
        lang = "ru"
    data = _load(lang)
    value = data.get(key)
    if value is None:
        # Fallback to Russian, then to raw key.
        value = _load("ru").get(key, key)
    if kwargs:
        try:
            return value.format(**kwargs)
        except (KeyError, IndexError):
            return value
    return value


def supported_languages() -> tuple[str, ...]:
    return _SUPPORTED


def language_title(lang: str) -> str:
    return {"ru": "🇷🇺 Русский", "en": "🇬🇧 English", "uk": "🇺🇦 Українська"}.get(
        lang, lang
    )
