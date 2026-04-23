# 🤖 ChatGPT Telegram Bot

Продвинутый Telegram-бот на базе OpenAI ChatGPT с монетизацией и админ-панелью — готов к продаже и запуску «из коробки».

## ✨ Возможности

- **Умный чат** — GPT-4o / GPT-4o-mini / GPT-4.1 / o4-mini (выбор модели прямо в боте)
- **Контекст диалога** — бот помнит последние N сообщений, автоматический тримминг по токенам
- **Роли ассистента** — переводчик, программист, психолог, SEO-копирайтер, юрист, учитель, бизнес-консультант и универсальный
- **Генерация картинок** — DALL·E 3 по команде `/image`
- **Голосовые сообщения** — бот распознаёт (Whisper) и отвечает
- **Монетизация**:
  - 💎 Подписки (несколько тарифов)
  - ⭐ Оплата через **Telegram Stars**
  - 💳 Оплата картой через **ЮKassa** (с вебхуками)
  - Бесплатные лимиты для новых пользователей
- **Реферальная программа** — бонусы за каждого приглашённого друга
- **Мультиязычность** — русский, английский, украинский (легко добавить новые)
- **Админ-панель** — статистика, рассылка всем пользователям, выдача подписки, блокировка
- **Продакшн-готовность** — async SQLAlchemy 2.0, Alembic-миграции, structlog, retry'и, Docker

---

## 🚀 Быстрый старт (5 минут)

### 1. Клонировать проект

```bash
git clone <ваш-репозиторий>
cd chatgpt-telegram-bot
```

### 2. Получить ключи

1. **Telegram Bot Token**: напишите [@BotFather](https://t.me/BotFather), команда `/newbot` — получите токен вида `123456:ABC...`
2. **OpenAI API Key**: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
3. **ЮKassa** (опционально): [yookassa.ru](https://yookassa.ru/) → подключите магазин, получите `shopId` и `secretKey`
4. **Telegram Stars**: включаются автоматически, ничего настраивать не нужно
5. Узнайте свой Telegram ID через [@userinfobot](https://t.me/userinfobot) — это будет `ADMIN_IDS`

### 3. Настроить `.env`

```bash
cp .env.example .env
nano .env  # заполнить токены
```

### 4. Запустить через Docker (рекомендуется)

```bash
docker compose up -d
docker compose logs -f bot
```

Бот готов. Откройте его в Telegram и напишите `/start`.

### 5. Или запустить локально

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
alembic upgrade head
python -m app
```

---

## 📋 Команды бота

| Команда     | Описание |
|-------------|----------|
| `/start`    | Приветствие, реферальная ссылка |
| `/help`     | Справка |
| `/menu`     | Главное меню с инлайн-кнопками |
| `/new`      | Очистить контекст диалога |
| `/role`     | Выбрать «роль» ассистента |
| `/model`    | Сменить модель GPT |
| `/image`    | Сгенерировать картинку (DALL·E 3) |
| `/profile`  | Профиль, лимиты, статус подписки |
| `/buy`      | Тарифы подписки |
| `/ref`      | Реферальная программа |
| `/lang`     | Сменить язык (🇷🇺 / 🇬🇧 / 🇺🇦) |

### Команды администратора

| Команда                      | Описание |
|------------------------------|----------|
| `/admin`                     | Админ-меню (статистика, рассылка) |
| `/grant <tg_id> <tariff>`    | Выдать подписку пользователю |
| `/block <tg_id>`             | Заблокировать |
| `/unblock <tg_id>`           | Разблокировать |

---

## ⚙️ Конфигурация (`.env`)

Все параметры — в `.env.example`. Основные:

| Переменная                    | Описание |
|-------------------------------|----------|
| `BOT_TOKEN`                   | Токен Telegram-бота от @BotFather |
| `OPENAI_API_KEY`              | Ключ OpenAI |
| `OPENAI_BASE_URL`             | (опц.) Для проксирования или OpenRouter |
| `ADMIN_IDS`                   | Telegram ID админов через запятую |
| `DATABASE_URL`                | SQLite по умолчанию, поддерживается Postgres |
| `FREE_DAILY_MESSAGES`         | Бесплатный лимит сообщений в сутки |
| `FREE_DAILY_IMAGES`           | Бесплатный лимит картинок в сутки |
| `FREE_DAILY_VOICES`           | Бесплатный лимит голосовых в сутки |
| `REFERRAL_BONUS_MESSAGES`     | Бонус сообщений за приглашение |
| `REFERRAL_BONUS_IMAGES`       | Бонус картинок за приглашение |
| `TARIFFS`                     | Список тарифов (формат описан в `.env.example`) |
| `YOOKASSA_SHOP_ID` / `YOOKASSA_SECRET_KEY` | Ключи ЮKassa (если используете) |
| `YOOKASSA_RETURN_URL`         | Куда возвращать клиента после оплаты (ссылка на бота) |
| `WEBHOOK_HOST`                | Публичный URL для ЮKassa webhook (опц.) |
| `WEBHOOK_PORT`                | Порт webhook-сервера (8080) |
| `DEFAULT_LANGUAGE`            | `ru` / `en` / `uk` |

### Формат тарифа

```
КОД|НАЗВАНИЕ|ДНИ|СООБЩЕНИЯ|КАРТИНКИ|ГОЛОСА|ЗВЁЗДЫ|РУБ
```

Пример (три тарифа через `;`):
```
basic|Базовый|30|500|20|30|150|299;pro|Про|30|2000|100|200|400|799;unlimited|Безлимит|30|100000|500|1000|1000|1990
```

---

## 🏗 Архитектура

```
app/
├── __main__.py              # Entry point (python -m app)
├── bot.py                   # Бутстрап бота, диспетчер, middlewares
├── config.py                # Pydantic-settings, парсинг .env и тарифов
├── logger.py                # structlog-логирование
├── webhook.py               # aiohttp-сервер для ЮKassa webhook
├── db/
│   ├── base.py              # SQLAlchemy Base
│   ├── models.py            # User, ChatMessage, Payment
│   ├── repositories.py      # Все запросы к БД
│   └── session.py           # Async engine / sessionmaker
├── handlers/
│   ├── common.py            # /start, /help, /profile, /new, /lang, /role, /model, /ref
│   ├── menu.py              # Инлайн-меню и переходы
│   ├── chat.py              # Основной чат с ChatGPT
│   ├── images.py            # DALL·E
│   ├── voice.py             # Whisper + ответ
│   ├── billing.py           # Telegram Stars + ЮKassa
│   └── admin.py             # Админ-панель и рассылка
├── keyboards/inline.py      # Все инлайн-клавиатуры
├── middlewares/user.py      # Создание/загрузка пользователя
├── services/
│   ├── openai_service.py    # Обёртка над OpenAI (chat/image/voice)
│   ├── chat_service.py      # Сборка контекста, запрос, сохранение
│   ├── yookassa_service.py  # ЮKassa SDK
│   ├── limits.py            # Подсчёт лимитов (подписка→бонусы→бесплатно)
│   └── roles.py             # Пресеты «ролей» ассистента
├── i18n/
│   ├── __init__.py          # translate(lang, key, **kwargs)
│   └── locales/ru.json, en.json, uk.json
alembic/                     # Миграции БД
Dockerfile
docker-compose.yml
pyproject.toml
```

### Стек

- **Python 3.11+**
- **aiogram 3.x** (async Telegram Bot API)
- **OpenAI Python SDK** (async)
- **SQLAlchemy 2.0 + aiosqlite / asyncpg**
- **Alembic** для миграций
- **pydantic-settings** для конфига
- **yookassa** SDK
- **structlog** для логов
- **tenacity** для retry'ев

---

## 🔧 Как работает монетизация

### Приоритет списания ресурсов

Когда пользователь отправляет сообщение / картинку / голосовое, бот списывает «1 единицу» по такому порядку:

1. **Активная подписка** (если есть остаток)
2. **Бонусы** (за рефералов)
3. **Дневной бесплатный лимит**

Если всё исчерпано — бот показывает предложение купить подписку.

### Telegram Stars

- Работает сразу после установки (провайдер — сам Telegram).
- Используется валюта `XTR`.
- Пользователь нажимает «⭐ Оплатить звёздами» → Telegram показывает нативный invoice → `successful_payment` прилетает в бота → подписка активируется автоматически.

### ЮKassa

1. Бот создаёт платёж, отправляет пользователю ссылку и кнопку «🔄 Проверить оплату».
2. Пользователь оплачивает картой.
3. Статус подписки проверяется по одному из двух путей:
   - **Вручную**: пользователь жмёт «Проверить оплату» — бот запрашивает статус у ЮKassa.
   - **Через webhook**: если вы настроили `WEBHOOK_HOST`, ЮKassa сама уведомляет бота — подписка активируется мгновенно, а пользователю приходит уведомление.

### Настройка webhook ЮKassa

1. Поднимите бота на публичном HTTPS-домене (Caddy / nginx + Let's Encrypt перед контейнером).
2. В `.env` установите `WEBHOOK_HOST=https://your-domain.tld`.
3. В [личном кабинете ЮKassa](https://yookassa.ru/my/api-keys-settings) добавьте URL:
   `https://your-domain.tld/yookassa/webhook` — событие `payment.succeeded`.
4. Перезапустите бота: `docker compose restart bot`.

---

## 🧑‍💼 Админ-панель

Войдите в бота с аккаунта, чей Telegram ID указан в `ADMIN_IDS`, и вызовите `/admin`. Доступно:

- **📊 Статистика**: всего пользователей, активных за 24ч / 7д, премиум-пользователей, общий доход в Stars и ₽.
- **📣 Рассылка**: отправить HTML-сообщение всем пользователям. Бот попросит подтверждение (`/confirm` или `/cancel`).
- **`/grant <tg_id> <tariff_code>`**: выдать подписку вручную (например, после ручного перевода).
- **`/block <tg_id>` / `/unblock <tg_id>`**: блокировка.

---

## 🌍 Мультиязычность

Локали — JSON-файлы в `app/i18n/locales/`. Чтобы добавить новый язык:

1. Скопируйте `ru.json` → `de.json` (например), переведите значения.
2. В `app/i18n/__init__.py` добавьте код языка в `_SUPPORTED`.
3. В `language_title()` добавьте название с флагом.

---

## 🗄 База данных

По умолчанию — **SQLite** (файл `./data/bot.db`). Для продакшна рекомендуется **PostgreSQL**:

1. Раскомментируйте секцию `postgres` в `docker-compose.yml`.
2. В `.env` замените `DATABASE_URL` на `postgresql+asyncpg://bot:botpass@postgres:5432/chatgpt_bot`.
3. `docker compose up -d` → миграции применятся автоматически при старте.

### Alembic

- Создать новую миграцию после изменения моделей:
  ```bash
  alembic revision --autogenerate -m "описание"
  ```
- Применить:
  ```bash
  alembic upgrade head
  ```

---

## 🛠 Деплой

### VPS (Ubuntu + Docker)

```bash
# На сервере
apt update && apt install -y docker.io docker-compose-plugin git
git clone <repo> /opt/chatgpt-bot
cd /opt/chatgpt-bot
cp .env.example .env && nano .env
docker compose up -d
```

Логи: `docker compose logs -f bot`. Перезапуск: `docker compose restart bot`.

### Railway / Fly.io / Render

Проект совместим с любым хостингом, умеющим собирать `Dockerfile`. Пробросьте volume `/app/data` или используйте Postgres.

---

## 💰 Продажа бота

При передаче покупателю:

1. **Передайте репозиторий** (архивом или как git-репо).
2. **Покупатель сам получает**: `BOT_TOKEN`, `OPENAI_API_KEY`, `YOOKASSA_SHOP_ID/SECRET`, `ADMIN_IDS` — ваши ключи не передаются.
3. **Инструкция покупателю**: запустить `docker compose up -d` после заполнения `.env`.
4. **Поддержка** (по желанию): предложите установку на VPS под ключ как отдельную услугу.

### Что «продаёт» бот сам по себе

- Качественная автоматическая монетизация (2 способа оплаты)
- Приятный UX (меню, роли, голосовые, картинки)
- Администрирование из Telegram (без отдельной веб-панели)
- Полностью готов к запуску — не нужно дописывать код

---

## 🧪 Разработка

```bash
# Установить dev-зависимости
pip install -e ".[dev]"

# Линтер
ruff check app
ruff check --fix app

# Типы
mypy app

# Тесты
pytest
```

---

## 📝 Лицензия

MIT — свободно используйте в коммерческих проектах.

---

## ❓ FAQ

**Q: Бот отвечает медленно.**
A: Модели `gpt-4o` и `gpt-4.1` заметно медленнее `gpt-4o-mini`. Сделайте `gpt-4o-mini` дефолтной в `.env` (`DEFAULT_CHAT_MODEL=gpt-4o-mini`) — ~10× быстрее и ~20× дешевле.

**Q: Нужен ли ИП/ООО для ЮKassa?**
A: Да, ЮKassa работает только с юрлицами и самозанятыми. Если только с Telegram Stars — ИП не нужен, Telegram сам удерживает комиссию.

**Q: Как увеличить лимит контекста?**
A: Поднимите `CONTEXT_MAX_MESSAGES` и `CONTEXT_MAX_TOKENS` в `.env`. Учтите — это увеличит расходы на OpenAI.

**Q: Можно подключить другие LLM (Claude, Gemini)?**
A: Укажите `OPENAI_BASE_URL` от OpenRouter/LiteLLM — бот будет работать с любой моделью, совместимой с OpenAI API.

**Q: Как посмотреть логи?**
A: `docker compose logs -f bot`. Уровень логирования — в `.env` (`LOG_LEVEL=DEBUG` для отладки).

---

Удачной продажи! 🚀
