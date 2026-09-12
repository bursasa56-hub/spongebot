# Telegram-бот для заработка звёзд

Бот, где пользователи зарабатывают Telegram Stars за рефералов (3★) и задания
(0.5★), а выводят подарками (15–100★) через ручное подтверждение админом.

## Установка

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # заполнить токен, админов, чат заявок
```

## Запуск

```bash
python run.py
```

## Тесты

```bash
python -m pytest -v
```

## Партнёрская интеграция

Партнёрский бот подтверждает выполнение задания:

```
POST /partner/confirm
{"api_key": "...", "user_id": 123, "task_id": 7}
```
