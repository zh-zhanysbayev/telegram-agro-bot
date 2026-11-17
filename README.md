# telegram-agro-bot

Telegram-бот на aiogram 3: опрашивает пользователя о состоянии культуры (почва, грибы, хмель) и передаёт ответы мультиагентной системе на базе Claude Code.

## Запуск

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
# впишите токен в .env: TELEGRAM_BOT_TOKEN=...
python bot.py
```

## Архитектура и API

### Адрес размещения
Бот работает локально на компьютере пользователя. Публичного домена или IP-адреса нет. Взаимодействие с Telegram происходит через метод Long Polling (исходящие запросы к `api.telegram.org`), поэтому Webhook и проброс портов не используются.

### Используемые API
- **Telegram Bot API** — приём сообщений и отправка ответов (библиотека aiogram 3).
- **Внутренний API вызова LLM** — бот использует модуль `subprocess` для вызова Claude Code CLI в папке `D:\!Working\living-soil-case`.

### Безопасность
Токен Telegram Bot API хранится в переменной окружения `.env` и не попадает в публичный репозиторий.

### Схема работы
```
Пользователь -> Telegram API -> bot.py (aiogram) -> subprocess (Claude CLI)
  -> Мультиагентная система (plant-advisors) -> ответ обратно в Telegram
```
