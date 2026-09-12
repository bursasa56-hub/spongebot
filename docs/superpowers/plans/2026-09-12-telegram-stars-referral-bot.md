# Telegram-бот для заработка звёзд — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Бот на aiogram, где пользователь зарабатывает Telegram Stars за приглашённых друзей (3★) и задания (0.5★), а выводит их подарком (15–100★) через ручное подтверждение админом.

**Architecture:** Модульный aiogram 3.x проект. SQLAlchemy 2.0 async + SQLite. Long polling + маленький aiohttp-сервер для подтверждений от партнёрских ботов. Middleware: сессия БД на апдейт, проверка обязательных спонсоров, фильтр админов. Баланс — целое число в десятых долях звезды (tenths).

**Tech Stack:** Python 3.11+, aiogram 3.x, SQLAlchemy 2.0 (async), aiosqlite, aiohttp, python-dotenv, pytest, pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-09-12-telegram-stars-referral-bot-design.md`

## Global Constraints

- Python 3.11+.
- Баланс — целое число tenths: 0.5★ = 5, 3★ = 30, 15★ = 150. Никогда не хранить деньги во float.
- Награда за реферала: **30 tenths** (`REFERRAL_REWARD_TENTHS = 30`).
- Награда за задание по умолчанию: **5 tenths**.
- Подарки: фиксированный список 15–100★ в `bot/utils/gifts.py`.
- Один друг засчитывается **один раз**; один спонсор — **один раз**; задание — **один раз** на пользователя.
- Обязательные спонсоры бывают `channel` и `bot`; проверка вживую через `getChatMember`.
- Канал добавляется в спонсоры только если **сам бот — админ** в канале.
- Админы и чат заявок — из `.env`.
- Интерфейс — русский. На каждом подэкране есть кнопка возврата в меню.
- Не коммитить секреты; `.env` в `.gitignore`.

---

## Файловая структура

| Файл | Ответственность |
|------|-----------------|
| `requirements.txt`, `.env.example`, `.gitignore` | зависимости и конфиг-шаблон |
| `bot/config.py` | чтение `.env` в dataclass `Config` |
| `bot/db/models.py` | ORM-модели |
| `bot/db/session.py` | engine, `init_db`, session factory, сидинг подарков |
| `bot/utils/gifts.py` | фиксированный каталог подарков |
| `bot/utils/stars.py` | формат/конверсия tenths |
| `bot/services/referral.py` | регистрация и начисление за друга |
| `bot/services/subscriptions.py` | обязательные спонсоры, разбор ссылок, проверка |
| `bot/services/tasks.py` | задания: доступные, выполнение |
| `bot/services/withdrawals.py` | создание/подтверждение заявок |
| `bot/services/stats.py` | статистика |
| `bot/services/partner_api.py` | aiohttp endpoint партнёров |
| `bot/keyboards/user.py`, `bot/keyboards/admin.py` | inline-клавиатуры |
| `bot/middlewares/db.py`, `subscription.py`, `admin_filter.py` | middleware |
| `bot/handlers/start.py`, `user.py`, `tasks.py`, `withdraw.py`, `admin.py` | роутеры |
| `bot/main.py`, `run.py` | сборка и запуск |
| `tests/*` | pytest |

---

### Task 1: Скаффолдинг проекта и конфиг

**Files:**
- Create: `requirements.txt`, `.env.example`, `.gitignore`, `bot/__init__.py`, `bot/config.py`, `tests/__init__.py`, `tests/conftest.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `Config` (frozen dataclass с полями `bot_token, admin_ids, admin_chat_id, support_url, partner_api_key, db_path, partner_api_host, partner_api_port`); `load_config(env_file: str | None = ".env") -> Config`.

- [ ] **Step 1: Создать файлы проекта**

`requirements.txt`:
```
aiogram>=3.4,<4
SQLAlchemy>=2.0,<3
aiosqlite>=0.19
aiohttp>=3.9
python-dotenv>=1.0
pytest>=8.0
pytest-asyncio>=0.23
```

`.env.example`:
```
BOT_TOKEN=
ADMIN_IDS=123456789,987654321
ADMIN_CHAT_ID=-1001234567890
SUPPORT_URL=https://t.me/support_username
PARTNER_API_KEY=change_me
DB_PATH=data/bot.db
PARTNER_API_HOST=0.0.0.0
PARTNER_API_PORT=8080
```

`.gitignore`:
```
__pycache__/
*.pyc
.env
data/
.pytest_cache/
.venv/
venv/
```

`bot/__init__.py` и `tests/__init__.py` — пустые.

- [ ] **Step 2: Написать падающий тест** `tests/test_config.py`

```python
from bot.config import load_config


def test_load_config(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123:abc")
    monkeypatch.setenv("ADMIN_IDS", "1, 2 ,3")
    monkeypatch.setenv("ADMIN_CHAT_ID", "-100")
    monkeypatch.setenv("SUPPORT_URL", "https://t.me/sup")
    monkeypatch.setenv("PARTNER_API_KEY", "key")
    monkeypatch.setenv("DB_PATH", "data/x.db")
    monkeypatch.setenv("PARTNER_API_PORT", "9090")

    cfg = load_config(None)

    assert cfg.bot_token == "123:abc"
    assert cfg.admin_ids == (1, 2, 3)
    assert cfg.admin_chat_id == -100
    assert cfg.support_url == "https://t.me/sup"
    assert cfg.partner_api_key == "key"
    assert cfg.db_path == "data/x.db"
    assert cfg.partner_api_port == 9090
    assert cfg.partner_api_host == "0.0.0.0"
```

- [ ] **Step 3: Запустить тест — убедиться, что падает**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL с `ModuleNotFoundError: No module named 'bot.config'`

- [ ] **Step 4: Реализовать** `bot/config.py`

```python
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: tuple[int, ...]
    admin_chat_id: int
    support_url: str
    partner_api_key: str
    db_path: str
    partner_api_host: str
    partner_api_port: int


def load_config(env_file: str | None = ".env") -> Config:
    if env_file:
        load_dotenv(env_file)
    admin_ids = tuple(
        int(part) for part in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if part
    )
    return Config(
        bot_token=os.environ["BOT_TOKEN"],
        admin_ids=admin_ids,
        admin_chat_id=int(os.environ["ADMIN_CHAT_ID"]),
        support_url=os.getenv("SUPPORT_URL", "https://t.me/telegram"),
        partner_api_key=os.getenv("PARTNER_API_KEY", "change_me"),
        db_path=os.getenv("DB_PATH", "data/bot.db"),
        partner_api_host=os.getenv("PARTNER_API_HOST", "0.0.0.0"),
        partner_api_port=int(os.getenv("PARTNER_API_PORT", "8080")),
    )
```

- [ ] **Step 5: Запустить тест — убедиться, что проходит**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 6: Коммит**

```bash
git add requirements.txt .env.example .gitignore bot/__init__.py bot/config.py tests/__init__.py tests/test_config.py
git commit -m "chore: project scaffolding and config loader"
```

---

### Task 2: ORM-модели, сессия и каталог подарков

**Files:**
- Create: `bot/utils/__init__.py`, `bot/utils/gifts.py`, `bot/db/__init__.py`, `bot/db/models.py`, `bot/db/session.py`
- Test: `tests/conftest.py`, `tests/test_db.py`

**Interfaces:**
- Consumes: ничего.
- Produces: `GiftSpec`, `FIXED_GIFTS`, `GIFTS_BY_ID`; модели `User, Sponsor, TaskItem, UserTask, Withdrawal, Broadcast, Gift`; `create_engine(db_path)`, `init_db(engine)`, `make_session_factory(engine)`. Поля моделей — как в спецификации §3.

- [ ] **Step 1: Создать каталог подарков** `bot/utils/gifts.py`

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GiftSpec:
    id: str
    name: str
    emoji: str
    stars: int


FIXED_GIFTS: tuple[GiftSpec, ...] = (
    GiftSpec("bear", "Медвежонок", "🧸", 15),
    GiftSpec("rabbit", "Плюшевый заяц", "🐰", 20),
    GiftSpec("rose", "Роза", "🌹", 25),
    GiftSpec("heart", "Сердце", "❤️", 30),
    GiftSpec("cake", "Тортик", "🎂", 35),
    GiftSpec("ring", "Кольцо", "💍", 40),
    GiftSpec("bouquet", "Букет", "💐", 50),
    GiftSpec("crown", "Корона", "👑", 60),
    GiftSpec("cup", "Кубок", "🏆", 75),
    GiftSpec("diamond", "Алмаз", "💎", 100),
)

GIFTS_BY_ID: dict[str, GiftSpec] = {gift.id: gift for gift in FIXED_GIFTS}
```

- [ ] **Step 2: Создать модели** `bot/db/models.py`

```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(255))
    referred_by: Mapped[int | None] = mapped_column(BigInteger)
    referral_credited: Mapped[bool] = mapped_column(Boolean, default=False)
    balance_tenths: Mapped[int] = mapped_column(Integer, default=0)
    total_earned_tenths: Mapped[int] = mapped_column(Integer, default=0)
    total_withdrawn_tenths: Mapped[int] = mapped_column(Integer, default=0)
    subscribed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Sponsor(Base):
    __tablename__ = "sponsors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(255))
    chat_id: Mapped[str | None] = mapped_column(String(64))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TaskItem(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(255))
    chat_id: Mapped[str | None] = mapped_column(String(64))
    reward_tenths: Mapped[int] = mapped_column(Integer, default=5)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class UserTask(Base):
    __tablename__ = "user_tasks"
    __table_args__ = (UniqueConstraint("user_id", "task_id", name="uq_user_task"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("tasks.id"))
    completed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    gift_id: Mapped[str] = mapped_column(String(32))
    gift_name: Mapped[str] = mapped_column(String(64))
    gift_stars: Mapped[int] = mapped_column(Integer)
    username_to: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    admin_chat_id: Mapped[int | None] = mapped_column(BigInteger)
    admin_msg_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime)


class Broadcast(Base):
    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(String)
    media_file_id: Mapped[str | None] = mapped_column(String(255))
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Gift(Base):
    __tablename__ = "gifts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    emoji: Mapped[str] = mapped_column(String(8))
    stars: Mapped[int] = mapped_column(Integer)
```

- [ ] **Step 3: Создать сессию** `bot/db/session.py`

```python
from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ..utils.gifts import FIXED_GIFTS
from .models import Base, Gift


def create_engine(db_path: str) -> AsyncEngine:
    if db_path == ":memory:":
        url = "sqlite+aiosqlite:///:memory:"
    else:
        url = f"sqlite+aiosqlite:///{db_path}"
    return create_async_engine(url, echo=False)


async def init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        existing = await session.get(Gift, FIXED_GIFTS[0].id)
        if existing is None:
            session.add_all(
                [
                    Gift(id=g.id, name=g.name, emoji=g.emoji, stars=g.stars)
                    for g in FIXED_GIFTS
                ]
            )
            await session.commit()


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
```

- [ ] **Step 4: Написать фикстуры** `tests/conftest.py`

```python
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.session import create_engine, init_db, make_session_factory


@pytest_asyncio.fixture
async def engine():
    eng = create_engine(":memory:")
    await init_db(eng)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    maker = make_session_factory(engine)
    async with maker() as s:
        yield s


@pytest_asyncio.fixture(autouse=True)
def anyio_backend():
    return "asyncio"
```

- [ ] **Step 5: Написать падающий тест** `tests/test_db.py`

```python
import pytest
from sqlalchemy import func, select

from bot.db.models import Gift, User
from bot.db.session import create_engine, init_db, make_session_factory
from bot.utils.gifts import FIXED_GIFTS


@pytest.mark.asyncio
async def test_init_db_creates_tables_and_seeds_gifts(engine, session):
    count = (await session.execute(select(func.count()).select_from(Gift))).scalar_one()
    assert count == len(FIXED_GIFTS)


@pytest.mark.asyncio
async def test_user_defaults(engine, session):
    session.add(User(id=1, username="a", first_name="A"))
    await session.commit()
    user = await session.get(User, 1)
    assert user.balance_tenths == 0
    assert user.referral_credited is False
    assert user.subscribed is False
```

Добавить в `tests/conftest.py` вверху `pytest_plugins = ("pytest_asyncio",)` не требуется, но нужен `asyncio_mode`. Создать `pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 6: Запустить тесты — убедиться, что проходят**

Run: `python -m pytest tests/test_db.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: Коммит**

```bash
git add pytest.ini bot/utils/ bot/db/ tests/conftest.py tests/test_db.py
git commit -m "feat: database models, session and gift catalog"
```

---

### Task 3: Форматирование звёзд

**Files:**
- Create: `bot/utils/stars.py`
- Test: `tests/test_stars.py`

**Interfaces:**
- Produces: `format_stars(tenths: int) -> str`, `stars_to_tenths(stars: float | int) -> int`.

- [ ] **Step 1: Написать падающий тест** `tests/test_stars.py`

```python
from bot.utils.stars import format_stars, stars_to_tenths


def test_format_whole():
    assert format_stars(30) == "3 ★"


def test_format_fraction():
    assert format_stars(5) == "0.5 ★"
    assert format_stars(35) == "3.5 ★"


def test_stars_to_tenths():
    assert stars_to_tenths(0.5) == 5
    assert stars_to_tenths(3) == 30
    assert stars_to_tenths(15) == 150
```

- [ ] **Step 2: Запустить — падает**

Run: `python -m pytest tests/test_stars.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: Реализовать** `bot/utils/stars.py`

```python
from __future__ import annotations


def format_stars(tenths: int) -> str:
    if tenths % 10 == 0:
        return f"{tenths // 10} ★"
    return f"{tenths / 10:.1f} ★"


def stars_to_tenths(stars: float | int) -> int:
    return int(round(float(stars) * 10))
```

- [ ] **Step 4: Запустить — проходит**

Run: `python -m pytest tests/test_stars.py -v`
Expected: PASS

- [ ] **Step 5: Коммит**

```bash
git add bot/utils/stars.py tests/test_stars.py
git commit -m "feat: star amount formatting utilities"
```

---

### Task 4: Сервис рефералов

**Files:**
- Create: `bot/services/__init__.py`, `bot/services/referral.py`
- Test: `tests/test_referral.py`

**Interfaces:**
- Consumes: модели `User`.
- Produces: `REFERRAL_REWARD_TENTHS = 30`; `get_user(session, user_id) -> User | None`; `register_user(session, user_id, username, first_name, ref_id=None) -> User`; `credit_referrer(session, friend_id) -> User | None` (возвращает пригласившего, если начисление произошло).

- [ ] **Step 1: Написать падающий тест** `tests/test_referral.py`

```python
import pytest

from bot.db.models import User
from bot.services.referral import (
    REFERRAL_REWARD_TENTHS,
    count_referrals,
    credit_referrer,
    register_user,
)


@pytest.mark.asyncio
async def test_register_new_user_with_referrer(session):
    await register_user(session, 1, "owner", "Owner")
    friend = await register_user(session, 2, "friend", "Friend", ref_id=1)
    assert friend.referred_by == 1
    assert friend.referral_credited is False


@pytest.mark.asyncio
async def test_self_referral_ignored(session):
    user = await register_user(session, 1, "a", "A", ref_id=1)
    assert user.referred_by is None


@pytest.mark.asyncio
async def test_credit_referrer_once(session):
    await register_user(session, 1, "owner", "Owner")
    await register_user(session, 2, "friend", "Friend", ref_id=1)

    referrer = await credit_referrer(session, 2)
    assert referrer is not None
    assert referrer.balance_tenths == REFERRAL_REWARD_TENTHS
    assert referrer.total_earned_tenths == REFERRAL_REWARD_TENTHS

    again = await credit_referrer(session, 2)
    assert again is None
    owner = await session.get(User, 1)
    assert owner.balance_tenths == REFERRAL_REWARD_TENTHS


@pytest.mark.asyncio
async def test_repeat_start_does_not_change_referrer(session):
    await register_user(session, 1, "owner", "Owner")
    await register_user(session, 2, "friend", "Friend", ref_id=1)
    user = await register_user(session, 2, "friend", "Friend", ref_id=99)
    assert user.referred_by == 1


@pytest.mark.asyncio
async def test_count_referrals(session):
    await register_user(session, 1, "owner", "Owner")
    await register_user(session, 2, "f1", "F1", ref_id=1)
    await register_user(session, 3, "f2", "F2", ref_id=1)
    await register_user(session, 4, "other", "O", ref_id=2)
    assert await count_referrals(session, 1) == 2
```

- [ ] **Step 2: Запустить — падает**

Run: `python -m pytest tests/test_referral.py -v`
Expected: FAIL `ModuleNotFoundError: bot.services.referral`

- [ ] **Step 3: Реализовать** `bot/services/referral.py`

```python
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import User

REFERRAL_REWARD_TENTHS = 30


async def get_user(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def register_user(
    session: AsyncSession,
    user_id: int,
    username: str | None,
    first_name: str | None,
    ref_id: int | None = None,
) -> User:
    user = await session.get(User, user_id)
    if user is None:
        user = User(id=user_id, username=username, first_name=first_name)
        if ref_id is not None and ref_id != user_id:
            user.referred_by = ref_id
        session.add(user)
    else:
        if username != user.username:
            user.username = username
        if first_name != user.first_name:
            user.first_name = first_name
    await session.commit()
    return user


async def credit_referrer(session: AsyncSession, friend_id: int) -> User | None:
    friend = await session.get(User, friend_id)
    if friend is None or friend.referred_by is None or friend.referral_credited:
        return None

    referrer = await session.get(User, friend.referred_by)
    friend.referral_credited = True
    if referrer is None:
        await session.commit()
        return None

    referrer.balance_tenths += REFERRAL_REWARD_TENTHS
    referrer.total_earned_tenths += REFERRAL_REWARD_TENTHS
    await session.commit()
    return referrer


async def count_referrals(session: AsyncSession, user_id: int) -> int:
    from sqlalchemy import func, select

    return (
        await session.execute(
            select(func.count()).select_from(User).where(User.referred_by == user_id)
        )
    ).scalar_one()
```

- [ ] **Step 4: Запустить — проходит**

Run: `python -m pytest tests/test_referral.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Коммит**

```bash
git add bot/services/__init__.py bot/services/referral.py tests/test_referral.py
git commit -m "feat: referral registration and one-time crediting"
```

---

### Task 5: Сервис обязательных спонсоров

**Files:**
- Create: `bot/services/subscriptions.py`
- Test: `tests/test_subscriptions.py`

**Interfaces:**
- Consumes: модель `Sponsor`.
- Produces: `SponsorError(Exception)`; `parse_chat_ref(text) -> str`; `is_member(bot, chat_ref, user_id) -> bool`; `active_sponsors(session) -> list[Sponsor]`; `missing_sponsors(session, bot, user_id) -> list[Sponsor]`; `add_channel_sponsor(session, bot, link) -> Sponsor`; `add_bot_sponsor(session, link) -> Sponsor`; `delete_sponsor(session, sponsor_id) -> bool`.

**Фейковый бот для тестов** (положить в `tests/fakes.py`):

```python
class FakeChat:
    def __init__(self, id, title="T", username=None):
        self.id = id
        self.title = title
        self.username = username


class FakeMember:
    def __init__(self, status):
        self.status = status


class FakeBot:
    def __init__(self, id=999, member_status="member", chat=None, raise_member=False):
        self.id = id
        self._member_status = member_status
        self._chat = chat
        self._raise_member = raise_member

    async def get_chat(self, chat_id):
        if self._chat is None:
            raise RuntimeError("no chat")
        return self._chat

    async def get_chat_member(self, chat_id, user_id):
        if self._raise_member:
            raise RuntimeError("not a member")
        return FakeMember(self._member_status)
```

- [ ] **Step 1: Написать падающий тест** `tests/test_subscriptions.py`

```python
import pytest

from bot.services.subscriptions import (
    SponsorError,
    add_bot_sponsor,
    add_channel_sponsor,
    active_sponsors,
    delete_sponsor,
    missing_sponsors,
    parse_chat_ref,
)
from tests.fakes import FakeBot, FakeChat


def test_parse_chat_ref_variants():
    assert parse_chat_ref("@my_channel") == "@my_channel"
    assert parse_chat_ref("https://t.me/my_channel") == "@my_channel"
    assert parse_chat_ref("t.me/my_channel/12") == "@my_channel"
    assert parse_chat_ref("-1001234567890") == "-1001234567890"


def test_parse_chat_ref_invalid():
    with pytest.raises(SponsorError):
        parse_chat_ref("https://t.me/+InviteHash")


@pytest.mark.asyncio
async def test_add_channel_sponsor_requires_bot_admin(session):
    bot = FakeBot(member_status="member", chat=FakeChat(-100, "Chan", "chan"))
    with pytest.raises(SponsorError):
        await add_channel_sponsor(session, bot, "@chan")


@pytest.mark.asyncio
async def test_add_channel_sponsor_success_and_no_duplicates(session):
    bot = FakeBot(member_status="administrator", chat=FakeChat(-100, "Chan", "chan"))
    sponsor = await add_channel_sponsor(session, bot, "@chan")
    assert sponsor.chat_id == "-100"
    assert sponsor.type == "channel"
    with pytest.raises(SponsorError):
        await add_channel_sponsor(session, bot, "@chan")


@pytest.mark.asyncio
async def test_add_bot_sponsor(session):
    sponsor = await add_bot_sponsor(session, "https://t.me/partner_bot")
    assert sponsor.type == "bot"
    assert sponsor.url == "https://t.me/partner_bot"


@pytest.mark.asyncio
async def test_missing_sponsors(session):
    await add_bot_sponsor(session, "@partner_bot")
    bot_ok = FakeBot(member_status="member")
    assert await missing_sponsors(session, bot_ok, 1) == []

    bot_no = FakeBot(raise_member=True)
    assert len(await missing_sponsors(session, bot_no, 1)) == 1


@pytest.mark.asyncio
async def test_delete_sponsor(session):
    sponsor = await add_bot_sponsor(session, "@partner_bot")
    assert await delete_sponsor(session, sponsor.id) is True
    assert await active_sponsors(session) == []
```

- [ ] **Step 2: Запустить — падает**

Run: `python -m pytest tests/test_subscriptions.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: Реализовать** `bot/services/subscriptions.py`

```python
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Sponsor

MEMBER_STATUSES = {"creator", "administrator", "member", "restricted"}


class SponsorError(Exception):
    pass


def parse_chat_ref(text: str) -> str:
    text = text.strip()
    if text.lstrip("-").isdigit():
        return text
    if "t.me/" in text:
        slug = text.split("t.me/", 1)[1].split("/")[0].split("?")[0]
    elif text.startswith("@"):
        slug = text[1:]
    else:
        slug = text
    if not slug or slug.startswith("+"):
        raise SponsorError(
            "Не удалось распознать ссылку. Отправьте @username, ссылку t.me/... или id -100..."
        )
    return "@" + slug


async def is_member(bot, chat_ref: str, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=chat_ref, user_id=user_id)
    except Exception:
        return False
    return getattr(member, "status", None) in MEMBER_STATUSES


async def active_sponsors(session: AsyncSession) -> list[Sponsor]:
    res = await session.execute(
        select(Sponsor).where(Sponsor.active.is_(True)).order_by(Sponsor.id)
    )
    return list(res.scalars().all())


async def missing_sponsors(session: AsyncSession, bot, user_id: int) -> list[Sponsor]:
    missing = []
    for sponsor in await active_sponsors(session):
        if not await is_member(bot, sponsor.chat_id or sponsor.url, user_id):
            missing.append(sponsor)
    return missing


async def add_channel_sponsor(session: AsyncSession, bot, link: str) -> Sponsor:
    chat_ref = parse_chat_ref(link)
    try:
        chat = await bot.get_chat(chat_ref)
    except Exception as exc:
        raise SponsorError(
            "Не удалось получить канал. Проверьте ссылку и что бот добавлен в канал."
        ) from exc

    try:
        me = await bot.get_chat_member(chat_id=chat.id, user_id=bot.id)
    except Exception as exc:
        raise SponsorError(
            "Бот не администратор этого канала. Добавьте бота в админы и повторите."
        ) from exc
    if getattr(me, "status", None) not in {"administrator", "creator"}:
        raise SponsorError(
            "Бот не администратор этого канала. Добавьте бота в админы и повторите."
        )

    existing = await session.execute(
        select(Sponsor).where(Sponsor.chat_id == str(chat.id))
    )
    if existing.scalar_one_or_none() is not None:
        raise SponsorError("Этот канал уже добавлен.")

    title = getattr(chat, "title", None) or chat_ref
    username = getattr(chat, "username", None)
    url = f"https://t.me/{username}" if username else str(chat.id)
    sponsor = Sponsor(type="channel", title=title, url=url, chat_id=str(chat.id))
    session.add(sponsor)
    await session.commit()
    return sponsor


async def add_bot_sponsor(session: AsyncSession, link: str) -> Sponsor:
    chat_ref = parse_chat_ref(link)
    username = chat_ref.lstrip("@")
    url = f"https://t.me/{username}"
    existing = await session.execute(select(Sponsor).where(Sponsor.url == url))
    if existing.scalar_one_or_none() is not None:
        raise SponsorError("Этот бот уже добавлен.")
    sponsor = Sponsor(type="bot", title="@" + username, url=url, chat_id=None)
    session.add(sponsor)
    await session.commit()
    return sponsor


async def delete_sponsor(session: AsyncSession, sponsor_id: int) -> bool:
    sponsor = await session.get(Sponsor, sponsor_id)
    if sponsor is None:
        return False
    await session.delete(sponsor)
    await session.commit()
    return True
```

- [ ] **Step 4: Запустить — проходит**

Run: `python -m pytest tests/test_subscriptions.py -v`
Expected: PASS

- [ ] **Step 5: Коммит**

```bash
git add bot/services/subscriptions.py tests/fakes.py tests/test_subscriptions.py
git commit -m "feat: mandatory sponsors service with live subscription checks"
```

---

### Task 6: Сервис заданий

**Files:**
- Create: `bot/services/tasks.py`
- Test: `tests/test_tasks.py`

**Interfaces:**
- Consumes: `TaskItem`, `UserTask`, `User`, `is_member` из `subscriptions`.
- Produces: `available_tasks(session, user_id) -> list[TaskItem]`; `complete_task(session, user_id, task_id) -> TaskItem | None` (идемпотентно); `is_channel_member(bot, chat_id, user_id) -> bool`.

- [ ] **Step 1: Написать падающий тест** `tests/test_tasks.py`

```python
import pytest

from bot.db.models import TaskItem, User
from bot.services.tasks import available_tasks, complete_task


async def _make_user(session, uid=1):
    session.add(User(id=uid, username="u", first_name="U"))
    await session.commit()


@pytest.mark.asyncio
async def test_complete_task_awards_once(session):
    await _make_user(session)
    task = TaskItem(type="channel", title="T", url="https://t.me/t", chat_id="@t")
    session.add(task)
    await session.commit()

    done = await complete_task(session, 1, task.id)
    assert done is not None
    user = await session.get(User, 1)
    assert user.balance_tenths == 5

    again = await complete_task(session, 1, task.id)
    assert again is None
    assert user.balance_tenths == 5


@pytest.mark.asyncio
async def test_available_excludes_completed(session):
    await _make_user(session)
    t1 = TaskItem(type="channel", title="T1", url="u1", chat_id="@t1")
    t2 = TaskItem(type="channel", title="T2", url="u2", chat_id="@t2")
    session.add_all([t1, t2])
    await session.commit()

    assert len(await available_tasks(session, 1)) == 2
    await complete_task(session, 1, t1.id)
    remaining = await available_tasks(session, 1)
    assert [t.id for t in remaining] == [t2.id]


@pytest.mark.asyncio
async def test_inactive_task_not_completable(session):
    await _make_user(session)
    task = TaskItem(type="channel", title="T", url="u", chat_id="@t", active=False)
    session.add(task)
    await session.commit()
    assert await complete_task(session, 1, task.id) is None
```

- [ ] **Step 2: Запустить — падает**

Run: `python -m pytest tests/test_tasks.py -v`
Expected: FAIL

- [ ] **Step 3: Реализовать** `bot/services/tasks.py`

```python
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import TaskItem, User, UserTask
from .subscriptions import is_member


async def available_tasks(session: AsyncSession, user_id: int) -> list[TaskItem]:
    done = select(UserTask.task_id).where(UserTask.user_id == user_id)
    res = await session.execute(
        select(TaskItem)
        .where(TaskItem.active.is_(True), TaskItem.id.not_in(done))
        .order_by(TaskItem.id)
    )
    return list(res.scalars().all())


async def complete_task(
    session: AsyncSession, user_id: int, task_id: int
) -> TaskItem | None:
    task = await session.get(TaskItem, task_id)
    if task is None or not task.active:
        return None

    already = await session.execute(
        select(UserTask).where(
            UserTask.user_id == user_id, UserTask.task_id == task_id
        )
    )
    if already.scalar_one_or_none() is not None:
        return None

    user = await session.get(User, user_id)
    if user is None:
        return None

    session.add(UserTask(user_id=user_id, task_id=task_id))
    user.balance_tenths += task.reward_tenths
    user.total_earned_tenths += task.reward_tenths
    await session.commit()
    return task


async def is_channel_member(bot, chat_id: str, user_id: int) -> bool:
    return await is_member(bot, chat_id, user_id)
```

- [ ] **Step 4: Запустить — проходит**

Run: `python -m pytest tests/test_tasks.py -v`
Expected: PASS

- [ ] **Step 5: Коммит**

```bash
git add bot/services/tasks.py tests/test_tasks.py
git commit -m "feat: one-time tasks service"
```

---

### Task 7: Сервис вывода звёзд

**Files:**
- Create: `bot/services/withdrawals.py`
- Test: `tests/test_withdrawals.py`

**Interfaces:**
- Consumes: `User`, `Withdrawal`.
- Produces: `WithdrawalError(Exception)`; `create_withdrawal(session, user_id, gift_id, gift_name, gift_stars, username_to) -> Withdrawal`; `mark_paid(session, withdrawal_id) -> Withdrawal | None` (идемпотентно, списывает баланс).

- [ ] **Step 1: Написать падающий тест** `tests/test_withdrawals.py`

```python
import pytest

from bot.db.models import User
from bot.services.withdrawals import (
    WithdrawalError,
    create_withdrawal,
    mark_paid,
)


async def _rich_user(session, uid=1, tenths=200):
    session.add(User(id=uid, username="u", first_name="U", balance_tenths=tenths))
    await session.commit()


@pytest.mark.asyncio
async def test_cannot_withdraw_more_than_balance(session):
    await _rich_user(session, tenths=100)
    with pytest.raises(WithdrawalError):
        await create_withdrawal(session, 1, "bear", "Медвежонок", 15, "@friend")


@pytest.mark.asyncio
async def test_create_and_mark_paid(session):
    await _rich_user(session, tenths=200)
    w = await create_withdrawal(session, 1, "bear", "Медвежонок", 15, "@friend")
    assert w.status == "pending"
    assert w.username_to == "friend"

    paid = await mark_paid(session, w.id)
    assert paid is not None
    assert paid.status == "paid"
    user = await session.get(User, 1)
    assert user.balance_tenths == 50
    assert user.total_withdrawn_tenths == 150


@pytest.mark.asyncio
async def test_mark_paid_idempotent(session):
    await _rich_user(session, tenths=200)
    w = await create_withdrawal(session, 1, "bear", "Медвежонок", 15, "@friend")
    await mark_paid(session, w.id)
    assert await mark_paid(session, w.id) is None
    user = await session.get(User, 1)
    assert user.balance_tenths == 50
```

- [ ] **Step 2: Запустить — падает**

Run: `python -m pytest tests/test_withdrawals.py -v`
Expected: FAIL

- [ ] **Step 3: Реализовать** `bot/services/withdrawals.py`

```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import User, Withdrawal


class WithdrawalError(Exception):
    pass


async def create_withdrawal(
    session: AsyncSession,
    user_id: int,
    gift_id: str,
    gift_name: str,
    gift_stars: int,
    username_to: str,
) -> Withdrawal:
    user = await session.get(User, user_id)
    if user is None:
        raise WithdrawalError("Пользователь не найден.")

    required = gift_stars * 10
    if user.balance_tenths < required:
        raise WithdrawalError("Недостаточно звёзд для этого подарка.")

    withdrawal = Withdrawal(
        user_id=user_id,
        gift_id=gift_id,
        gift_name=gift_name,
        gift_stars=gift_stars,
        username_to=username_to.lstrip("@"),
        status="pending",
    )
    session.add(withdrawal)
    await session.commit()
    return withdrawal


async def mark_paid(session: AsyncSession, withdrawal_id: int) -> Withdrawal | None:
    withdrawal = await session.get(Withdrawal, withdrawal_id)
    if withdrawal is None or withdrawal.status == "paid":
        return None

    user = await session.get(User, withdrawal.user_id)
    required = withdrawal.gift_stars * 10
    if user is None or user.balance_tenths < required:
        return None

    user.balance_tenths -= required
    user.total_withdrawn_tenths += required
    withdrawal.status = "paid"
    withdrawal.paid_at = datetime.utcnow()
    await session.commit()
    return withdrawal
```

- [ ] **Step 4: Запустить — проходит**

Run: `python -m pytest tests/test_withdrawals.py -v`
Expected: PASS

- [ ] **Step 5: Коммит**

```bash
git add bot/services/withdrawals.py tests/test_withdrawals.py
git commit -m "feat: withdrawal requests with idempotent payout"
```

---

### Task 8: Сервис статистики

**Files:**
- Create: `bot/services/stats.py`
- Test: `tests/test_stats.py`

**Interfaces:**
- Produces: `Stats` dataclass (`total_users, new_today, new_week, new_month, referrals, earned_tenths, withdrawn_tenths, pending_withdrawals, tasks_done`); `get_stats(session) -> Stats`.

- [ ] **Step 1: Написать падающий тест** `tests/test_stats.py`

```python
from datetime import datetime, timedelta

import pytest

from bot.db.models import User, Withdrawal
from bot.services.stats import get_stats


@pytest.mark.asyncio
async def test_stats_counts(session):
    now = datetime.utcnow()
    session.add_all(
        [
            User(id=1, created_at=now, balance_tenths=30, total_earned_tenths=30),
            User(id=2, created_at=now - timedelta(days=3), referred_by=1),
            User(id=3, created_at=now - timedelta(days=40)),
        ]
    )
    session.add(
        Withdrawal(
            user_id=1,
            gift_id="bear",
            gift_name="Медвежонок",
            gift_stars=15,
            username_to="x",
            status="pending",
        )
    )
    await session.commit()

    stats = await get_stats(session)
    assert stats.total_users == 3
    assert stats.new_today == 1
    assert stats.new_week == 2
    assert stats.new_month == 2
    assert stats.referrals == 1
    assert stats.earned_tenths == 30
    assert stats.pending_withdrawals == 1
```

- [ ] **Step 2: Запустить — падает**

Run: `python -m pytest tests/test_stats.py -v`
Expected: FAIL

- [ ] **Step 3: Реализовать** `bot/services/stats.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import User, UserTask, Withdrawal


@dataclass
class Stats:
    total_users: int
    new_today: int
    new_week: int
    new_month: int
    referrals: int
    earned_tenths: int
    withdrawn_tenths: int
    pending_withdrawals: int
    tasks_done: int


async def _count(session: AsyncSession, query) -> int:
    return (await session.execute(query)).scalar_one()


async def get_stats(session: AsyncSession) -> Stats:
    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    return Stats(
        total_users=await _count(session, select(func.count()).select_from(User)),
        new_today=await _count(
            session, select(func.count()).select_from(User).where(User.created_at >= day_ago)
        ),
        new_week=await _count(
            session, select(func.count()).select_from(User).where(User.created_at >= week_ago)
        ),
        new_month=await _count(
            session,
            select(func.count()).select_from(User).where(User.created_at >= month_start),
        ),
        referrals=await _count(
            session,
            select(func.count())
            .select_from(User)
            .where(User.referral_credited.is_(True)),
        ),
        earned_tenths=await _count(
            session, select(func.coalesce(func.sum(User.total_earned_tenths), 0))
        ),
        withdrawn_tenths=await _count(
            session, select(func.coalesce(func.sum(User.total_withdrawn_tenths), 0))
        ),
        pending_withdrawals=await _count(
            session,
            select(func.count())
            .select_from(Withdrawal)
            .where(Withdrawal.status == "pending"),
        ),
        tasks_done=await _count(
            session, select(func.count()).select_from(UserTask)
        ),
    )
```

- [ ] **Step 4: Запустить — проходит**

Run: `python -m pytest tests/test_stats.py -v`
Expected: PASS

- [ ] **Step 5: Коммит**

```bash
git add bot/services/stats.py tests/test_stats.py
git commit -m "feat: bot statistics service"
```

---

### Task 9: Партнёрский HTTP API

**Files:**
- Create: `bot/services/partner_api.py`
- Test: `tests/test_partner_api.py`

**Interfaces:**
- Consumes: `TaskItem`, `complete_task`, `make_session_factory`.
- Produces: `create_partner_app(session_factory, api_key) -> web.Application` с маршрутом `POST /partner/confirm`.

- [ ] **Step 1: Написать падающий тест** `tests/test_partner_api.py`

```python
import pytest
from aiohttp.test_utils import TestClient, TestServer

from bot.db.models import TaskItem, User
from bot.db.session import make_session_factory
from bot.services.partner_api import create_partner_app


@pytest.mark.asyncio
async def test_partner_confirm_flow(engine, session):
    session.add(User(id=5, username="u", first_name="U"))
    task = TaskItem(type="bot", title="B", url="https://t.me/b", active=True)
    session.add(task)
    await session.commit()
    task_id = task.id

    factory = make_session_factory(engine)
    app = create_partner_app(factory, "secret")
    client = TestClient(TestServer(app))
    await client.start_server()

    bad = await client.post(
        "/partner/confirm",
        json={"api_key": "wrong", "user_id": 5, "task_id": task_id},
    )
    assert bad.status == 403

    ok = await client.post(
        "/partner/confirm",
        json={"api_key": "secret", "user_id": 5, "task_id": task_id},
    )
    assert ok.status == 200
    body = await ok.json()
    assert body["credited"] is True

    again = await client.post(
        "/partner/confirm",
        json={"api_key": "secret", "user_id": 5, "task_id": task_id},
    )
    assert (await again.json())["credited"] is False

    await client.close()
```

- [ ] **Step 2: Запустить — падает**

Run: `python -m pytest tests/test_partner_api.py -v`
Expected: FAIL

- [ ] **Step 3: Реализовать** `bot/services/partner_api.py`

```python
from __future__ import annotations

from aiohttp import web

from ..db.models import TaskItem
from .tasks import complete_task


def create_partner_app(session_factory, api_key: str) -> web.Application:
    app = web.Application()

    async def confirm(request: web.Request) -> web.Response:
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "bad_json"}, status=400)

        if data.get("api_key") != api_key:
            return web.json_response({"ok": False, "error": "forbidden"}, status=403)

        try:
            user_id = int(data["user_id"])
            task_id = int(data["task_id"])
        except (KeyError, TypeError, ValueError):
            return web.json_response({"ok": False, "error": "bad_payload"}, status=400)

        async with session_factory() as session:
            task = await session.get(TaskItem, task_id)
            if task is None or not task.active or task.type != "bot":
                return web.json_response(
                    {"ok": False, "error": "task_not_found"}, status=404
                )
            done = await complete_task(session, user_id, task_id)
            return web.json_response({"ok": True, "credited": done is not None})

    app.router.add_post("/partner/confirm", confirm)
    return app
```

- [ ] **Step 4: Запустить — проходит**

Run: `python -m pytest tests/test_partner_api.py -v`
Expected: PASS

- [ ] **Step 5: Коммит**

```bash
git add bot/services/partner_api.py tests/test_partner_api.py
git commit -m "feat: partner bot confirmation endpoint"
```

---

### Task 10: Клавиатуры

**Files:**
- Create: `bot/keyboards/__init__.py`, `bot/keyboards/user.py`, `bot/keyboards/admin.py`
- Test: `tests/test_keyboards.py`

**Interfaces:**
- Produces (callback data): `MENU_MAIN="menu:main"`, `MENU_PROFILE="menu:profile"`, `MENU_INSTRUCTION="menu:instruction"`, `MENU_TASKS="menu:tasks"`, `MENU_WITHDRAW="menu:withdraw"`, `MENU_EARN="menu:earn"`, `CHECK_SUBS="check_subs"`.
- Produces функции: `main_menu_kb()`, `back_kb()`, `sponsor_gate_kb(sponsors)`, `instruction_kb(support_url)`, `task_kb(task)`, `earn_kb(ref_link)`, `gifts_kb(balance_tenths)`, `cancel_kb()`, `admin_menu_kb()`, `sponsors_admin_kb(sponsors)`, `tasks_admin_kb(tasks)`, `withdraw_admin_kb(withdrawal_id, username_to)`.

- [ ] **Step 1: Написать падающий тест** `tests/test_keyboards.py`

```python
from bot.db.models import Sponsor, TaskItem
from bot.keyboards.user import gifts_kb, main_menu_kb, task_kb
from bot.utils.gifts import FIXED_GIFTS


def _callbacks(kb):
    return [b.callback_data for row in kb.inline_keyboard for b in row]


def test_main_menu_has_all_buttons():
    data = _callbacks(main_menu_kb())
    for expected in [
        "menu:profile",
        "menu:instruction",
        "menu:tasks",
        "menu:withdraw",
        "menu:earn",
    ]:
        assert expected in data


def test_gifts_kb_only_affordable():
    kb = gifts_kb(200)
    ids = [b.callback_data for row in kb.inline_keyboard for b in row]
    assert "wd:gift:bear" in ids
    assert "wd:gift:rose" not in ids


def test_task_kb_has_check_and_skip():
    task = TaskItem(id=7, type="channel", title="T", url="u", chat_id="@t")
    data = _callbacks(task_kb(task))
    assert "task:check:7" in data
    assert "task:skip:7" in data
```

- [ ] **Step 2: Запустить — падает**

Run: `python -m pytest tests/test_keyboards.py -v`
Expected: FAIL

- [ ] **Step 3: Реализовать** `bot/keyboards/user.py`

```python
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..utils.gifts import FIXED_GIFTS
from ..utils.stars import format_stars

MENU_MAIN = "menu:main"
MENU_PROFILE = "menu:profile"
MENU_INSTRUCTION = "menu:instruction"
MENU_TASKS = "menu:tasks"
MENU_WITHDRAW = "menu:withdraw"
MENU_EARN = "menu:earn"
CHECK_SUBS = "check_subs"


def _btn(text: str, callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data)


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("👤 Профиль", MENU_PROFILE)],
            [_btn("📋 Задания", MENU_TASKS)],
            [_btn("💸 Вывод звёзд", MENU_WITHDRAW)],
            [_btn("💰 Заработать звёзды", MENU_EARN)],
            [_btn("📖 Инструкция", MENU_INSTRUCTION)],
        ]
    )


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[_btn("⬅️ Назад", MENU_MAIN)]])


def sponsor_gate_kb(sponsors) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"➡️ {s.title}", url=s.url)] for s in sponsors
    ]
    rows.append([_btn("✅ Проверить подписку", CHECK_SUBS)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def instruction_kb(support_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🆘 Поддержка", url=support_url)],
            [_btn("⬅️ Назад", MENU_MAIN)],
        ]
    )


def task_kb(task) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("✅ Проверить", f"task:check:{task.id}")],
            [_btn("⏭ Пропустить", f"task:skip:{task.id}")],
            [_btn("⬅️ Назад", MENU_MAIN)],
        ]
    )


def earn_kb(ref_link: str) -> InlineKeyboardMarkup:
    share = f"https://t.me/share/url?url={ref_link}&text=Заработай звёзды!"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📤 Поделиться", url=share)],
            [_btn("⬅️ Назад", MENU_MAIN)],
        ]
    )


def gifts_kb(balance_tenths: int) -> InlineKeyboardMarkup:
    rows = []
    for gift in FIXED_GIFTS:
        if gift.stars * 10 <= balance_tenths:
            rows.append(
                [
                    _btn(
                        f"{gift.emoji} {gift.name} — {format_stars(gift.stars * 10)}",
                        f"wd:gift:{gift.id}",
                    )
                ]
            )
    rows.append([_btn("⬅️ Назад", MENU_MAIN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[_btn("⬅️ Назад", MENU_MAIN)]])
```

- [ ] **Step 4: Реализовать** `bot/keyboards/admin.py`

```python
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def _btn(text: str, callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data)


def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("📢 Спонсоры", "admin:sponsors")],
            [_btn("📋 Задания", "admin:tasks")],
            [_btn("✉️ Рассылка", "admin:broadcast")],
            [_btn("📊 Статистика", "admin:stats")],
            [_btn("💸 Заявки на вывод", "admin:withdrawals")],
        ]
    )


def sponsors_admin_kb(sponsors) -> InlineKeyboardMarkup:
    rows = [[_btn("➕ Добавить канал", "admin:sponsor:add_channel")],
            [_btn("➕ Добавить бота", "admin:sponsor:add_bot")]]
    for s in sponsors:
        rows.append([_btn(f"🗑 {s.title}", f"admin:sponsor:del:{s.id}")])
    rows.append([_btn("⬅️ Назад", "admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def tasks_admin_kb(tasks) -> InlineKeyboardMarkup:
    rows = [[_btn("➕ Добавить задание", "admin:task:add")]]
    for t in tasks:
        rows.append([_btn(f"🗑 {t.title}", f"admin:task:del:{t.id}")])
    rows.append([_btn("⬅️ Назад", "admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def withdraw_admin_kb(withdrawal_id: int, username_to: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 Профиль заказчика", url=f"https://t.me/{username_to}")],
            [_btn("✅ Выплачено", f"wd:paid:{withdrawal_id}")],
        ]
    )
```

- [ ] **Step 5: Запустить — проходит**

Run: `python -m pytest tests/test_keyboards.py -v`
Expected: PASS

- [ ] **Step 6: Коммит**

```bash
git add bot/keyboards/ tests/test_keyboards.py
git commit -m "feat: inline keyboards for user and admin"
```

---

### Task 11: Middleware (сессия БД, гейт спонсоров, фильтр админов)

**Files:**
- Create: `bot/middlewares/__init__.py`, `bot/middlewares/db.py`, `bot/middlewares/subscription.py`, `bot/middlewares/admin_filter.py`
- Test: `tests/test_subscription_gate.py`

**Interfaces:**
- Produces: `DbSessionMiddleware(session_factory)`; `SubscriptionMiddleware(admin_ids)`; `IsAdmin(admin_ids)` (фильтр).

**Логика гейта:** пропускает `/start`, callback `check_subs`, любые `admin:*` и админов. Для остальных — если есть `missing_sponsors`, отправляет экран подписки и прерывает обработку.

- [ ] **Step 1: Написать падающий тест** `tests/test_subscription_gate.py`

Тестируем чистую функцию `should_skip_gate` из middleware.

```python
from bot.middlewares.subscription import should_skip_gate


class FakeUser:
    def __init__(self, uid):
        self.id = uid


class FakeMessage:
    def __init__(self, text, uid=1):
        self.text = text
        self.from_user = FakeUser(uid)


class FakeCallback:
    def __init__(self, data, uid=1):
        self.data = data
        self.from_user = FakeUser(uid)


def test_skip_start_and_gate_callbacks():
    assert should_skip_gate(FakeMessage("/start"), {}) is True
    assert should_skip_gate(FakeCallback("check_subs"), {}) is True
    assert should_skip_gate(FakeCallback("admin:menu"), {}) is True
    assert should_skip_gate(FakeMessage("привет"), {}) is False


def test_admins_skip_gate():
    assert should_skip_gate(FakeMessage("hi", uid=7), {7}) is True
    assert should_skip_gate(FakeMessage("hi", uid=8), {7}) is False
```

- [ ] **Step 2: Запустить — падает**

Run: `python -m pytest tests/test_subscription_gate.py -v`
Expected: FAIL

- [ ] **Step 3: Реализовать** `bot/middlewares/db.py`

```python
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class DbSessionMiddleware(BaseMiddleware):
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self.session_factory() as session:
            data["session"] = session
            return await handler(event, data)
```

- [ ] **Step 4: Реализовать** `bot/middlewares/admin_filter.py`

```python
from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject


class IsAdmin(BaseFilter):
    def __init__(self, admin_ids):
        self.admin_ids = set(admin_ids)

    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        return user is not None and user.id in self.admin_ids
```

- [ ] **Step 5: Реализовать** `bot/middlewares/subscription.py`

```python
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from ..keyboards.user import sponsor_gate_kb
from ..services.subscriptions import missing_sponsors


def should_skip_gate(event: TelegramObject, admin_ids) -> bool:
    user = getattr(event, "from_user", None)
    if user is not None and user.id in admin_ids:
        return True
    if isinstance(event, Message) and event.text and event.text.startswith("/start"):
        return True
    if isinstance(event, CallbackQuery) and event.data:
        if event.data == "check_subs" or event.data.startswith("admin:"):
            return True
    return False


class SubscriptionMiddleware(BaseMiddleware):
    def __init__(self, admin_ids):
        self.admin_ids = set(admin_ids)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if should_skip_gate(event, self.admin_ids):
            return await handler(event, data)

        session = data["session"]
        bot = data["bot"]
        user = event.from_user
        missing = await missing_sponsors(session, bot, user.id)
        if not missing:
            return await handler(event, data)

        text = (
            "🔒 Чтобы пользоваться ботом, подпишитесь на спонсоров ниже "
            "и нажмите «Проверить подписку»."
        )
        kb = sponsor_gate_kb(missing)
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text, reply_markup=kb)
            await event.answer()
        else:
            await event.answer(text, reply_markup=kb)
        return None
```

- [ ] **Step 6: Запустить — проходит**

Run: `python -m pytest tests/test_subscription_gate.py -v`
Expected: PASS

- [ ] **Step 7: Коммит**

```bash
git add bot/middlewares/ tests/test_subscription_gate.py
git commit -m "feat: db session, subscription gate and admin middlewares"
```

---

### Task 12: Обработчик старта и гейта подписок

**Files:**
- Create: `bot/handlers/__init__.py`, `bot/handlers/start.py`
- Test: `tests/test_start_helpers.py`

**Interfaces:**
- Consumes: `register_user`, `credit_referrer`, `missing_sponsors`, keyboards, `MENU_MAIN`.
- Produces: `parse_ref(payload: str | None) -> int | None`; `Router` (`router_start`).

- [ ] **Step 1: Написать падающий тест** `tests/test_start_helpers.py`

```python
from bot.handlers.start import parse_ref


def test_parse_ref():
    assert parse_ref("ref_123") == 123
    assert parse_ref("/start ref_5") == 5
    assert parse_ref(None) is None
    assert parse_ref("garbage") is None
    assert parse_ref("ref_abc") is None
```

- [ ] **Step 2: Запустить — падает**

Run: `python -m pytest tests/test_start_helpers.py -v`
Expected: FAIL

- [ ] **Step 3: Реализовать** `bot/handlers/start.py`

```python
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message

from ..keyboards.user import CHECK_SUBS, MENU_MAIN, main_menu_kb, sponsor_gate_kb
from ..services.referral import credit_referrer, register_user
from ..services.subscriptions import missing_sponsors
from ..utils.stars import format_stars

router_start = Router()

WELCOME = "👋 Добро пожаловать в бота для заработка звёзд!"


def parse_ref(payload: str | None) -> int | None:
    if not payload:
        return None
    token = payload.strip().split()[-1]
    if token.startswith("ref_"):
        token = token[4:]
    if token.isdigit():
        return int(token)
    return None


async def _show_menu(message: Message, user_id: int, edit: bool = False) -> None:
    text = (
        f"{WELCOME}\n\n"
        "Выбери раздел в меню ниже."
    )
    if edit:
        await message.edit_text(text, reply_markup=main_menu_kb())
    else:
        await message.answer(text, reply_markup=main_menu_kb())


@router_start.message(CommandStart())
async def cmd_start(
    message: Message, command: CommandObject, session, bot
) -> None:
    user = message.from_user
    ref_id = parse_ref(command.args)
    await register_user(session, user.id, user.username, user.first_name, ref_id)

    missing = await missing_sponsors(session, bot, user.id)
    if missing:
        await message.answer(
            "🔒 Для доступа подпишитесь на спонсоров и нажмите «Проверить подписку».",
            reply_markup=sponsor_gate_kb(missing),
        )
        return

    await _show_menu(message, user.id)


@router_start.callback_query(F.data == CHECK_SUBS)
async def check_subs(callback: CallbackQuery, session, bot) -> None:
    user = callback.from_user
    missing = await missing_sponsors(session, bot, user.id)
    if missing:
        await callback.answer("❌ Вы подписались не на всех спонсоров.", show_alert=True)
        await callback.message.edit_text(
            "🔒 Подпишитесь на спонсоров и нажмите «Проверить подписку».",
            reply_markup=sponsor_gate_kb(missing),
        )
        return

    referrer = await credit_referrer(session, user.id)
    if referrer is not None:
        try:
            await bot.send_message(
                referrer.id,
                f"🎉 По вашей ссылке зарегистрировался друг! Начислено "
                f"{format_stars(30)}.",
            )
        except Exception:
            pass

    await callback.answer("✅ Подписка подтверждена!")
    await callback.message.edit_text(
        f"{WELCOME}\n\nВыбери раздел в меню ниже.", reply_markup=main_menu_kb()
    )


@router_start.callback_query(F.data == MENU_MAIN)
async def back_to_main(callback: CallbackQuery, session, bot) -> None:
    missing = await missing_sponsors(session, bot, callback.from_user.id)
    if missing:
        await callback.message.edit_text(
            "🔒 Подпишитесь на спонсоров и нажмите «Проверить подписку».",
            reply_markup=sponsor_gate_kb(missing),
        )
        await callback.answer()
        return
    await callback.message.edit_text(
        f"{WELCOME}\n\nВыбери раздел в меню ниже.", reply_markup=main_menu_kb()
    )
    await callback.answer()
```

- [ ] **Step 4: Запустить — проходит**

Run: `python -m pytest tests/test_start_helpers.py -v`
Expected: PASS

- [ ] **Step 5: Коммит**

```bash
git add bot/handlers/__init__.py bot/handlers/start.py tests/test_start_helpers.py
git commit -m "feat: start command, referral parsing and subscription gate"
```

---

### Task 13: Пользовательские экраны (профиль, инструкция, заработать)

**Files:**
- Create: `bot/handlers/user.py`
- Test: `tests/test_user_texts.py`

**Interfaces:**
- Produces: `profile_text(user, bot_username, invited) -> str`; `count_referrals(session, user_id) -> int` (в `services/referral.py`); `Router` (`router_user`).

- [ ] **Step 1: Написать падающий тест** `tests/test_user_texts.py`

```python
from bot.db.models import User
from bot.handlers.user import profile_text


def test_profile_text_contains_stats():
    user = User(
        id=1,
        username="u",
        first_name="U",
        balance_tenths=35,
        total_earned_tenths=80,
        total_withdrawn_tenths=45,
    )
    text = profile_text(user, "my_bot", 2)
    assert "3.5 ★" in text
    assert "my_bot" in text
    assert "2" in text
```

- [ ] **Step 2: Запустить — падает**

Run: `python -m pytest tests/test_user_texts.py -v`
Expected: FAIL

- [ ] **Step 3: Реализовать** `bot/handlers/user.py`

```python
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from ..keyboards.user import (
    MENU_EARN,
    MENU_INSTRUCTION,
    MENU_PROFILE,
    back_kb,
    earn_kb,
    instruction_kb,
)
from ..services.referral import get_user
from ..utils.stars import format_stars

router_user = Router()

INSTRUCTION_TEXT = (
    "📖 <b>Как заработать звёзды</b>\n\n"
    "1. Приглашай друзей по своей реферальной ссылке — за каждого друга, "
    "который подпишется на всех спонсоров, ты получаешь 3 ★.\n"
    "2. Выполняй задания в разделе «Задания» — по 0.5 ★ за каждое.\n"
    "3. Оставляй ссылку в описании профиля и делись с друзьями.\n\n"
    "Звёзды можно вывести подарком (от 15 до 100 ★) в разделе «Вывод звёзд».\n\n"
    "Если что-то не работает — напиши в поддержку."
)


def profile_text(user, bot_username: str, invited: int) -> str:
    ref_link = f"https://t.me/{bot_username}?start=ref_{user.id}"
    return (
        "👤 <b>Твой профиль</b>\n\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"👥 Приглашено друзей: {invited}\n"
        f"💰 Баланс: {format_stars(user.balance_tenths)}\n"
        f"📈 Всего заработано: {format_stars(user.total_earned_tenths)}\n"
        f"💸 Всего выведено: {format_stars(user.total_withdrawn_tenths)}\n\n"
        f"🔗 Твоя ссылка:\n<code>{ref_link}</code>"
    )


@router_user.callback_query(F.data == MENU_PROFILE)
async def show_profile(callback: CallbackQuery, session, bot) -> None:
    user = await get_user(session, callback.from_user.id)
    invited = await count_referrals(session, user.id)
    me = await bot.get_me()
    await callback.message.edit_text(
        profile_text(user, me.username, invited), reply_markup=back_kb()
    )
    await callback.answer()


@router_user.callback_query(F.data == MENU_INSTRUCTION)
async def show_instruction(callback: CallbackQuery, support_url: str) -> None:
    await callback.message.edit_text(
        INSTRUCTION_TEXT, reply_markup=instruction_kb(support_url)
    )
    await callback.answer()


@router_user.callback_query(F.data == MENU_EARN)
async def show_earn(callback: CallbackQuery, bot) -> None:
    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{callback.from_user.id}"
    text = (
        "💰 <b>Как заработать звёзды</b>\n\n"
        "• Отправляй реферальную ссылку друзьям и родственникам.\n"
        "• Оставь ссылку в описании своего профиля.\n"
        "• Публикуй её в чатах и каналах.\n\n"
        "За каждого друга, который подпишется на всех спонсоров — 3 ★.\n\n"
        f"🔗 Твоя ссылка:\n<code>{ref_link}</code>"
    )
    await callback.message.edit_text(text, reply_markup=earn_kb(ref_link))
    await callback.answer()
```

`count_referrals` определена в Task 4.

- [ ] **Step 4: Запустить — проходит**

Run: `python -m pytest tests/test_user_texts.py -v`
Expected: PASS

- [ ] **Step 5: Коммит**

```bash
git add bot/handlers/user.py bot/services/referral.py tests/test_user_texts.py
git commit -m "feat: profile, instruction and earn screens"
```

---

### Task 14: Обработчик заданий

**Files:**
- Create: `bot/handlers/tasks.py`
- Test: `tests/test_tasks_flow.py`

**Interfaces:**
- Consumes: `available_tasks`, `complete_task`, `is_channel_member`, `task_kb`.
- Produces: `next_task(session, user_id, exclude_id=None) -> TaskItem | None`; `Router` (`router_tasks`).

- [ ] **Step 1: Написать падающий тест** `tests/test_tasks_flow.py`

```python
import pytest

from bot.db.models import TaskItem, User
from bot.handlers.tasks import next_task
from bot.services.tasks import complete_task


@pytest.mark.asyncio
async def test_next_task_skips_excluded(session):
    session.add(User(id=1, username="u", first_name="U"))
    t1 = TaskItem(type="channel", title="T1", url="u1", chat_id="@t1")
    t2 = TaskItem(type="channel", title="T2", url="u2", chat_id="@t2")
    session.add_all([t1, t2])
    await session.commit()

    first = await next_task(session, 1)
    assert first.id == t1.id
    second = await next_task(session, 1, exclude_id=t1.id)
    assert second.id == t2.id
    await complete_task(session, 1, t2.id)
    assert await next_task(session, 1) is None
```

- [ ] **Step 2: Запустить — падает**

Run: `python -m pytest tests/test_tasks_flow.py -v`
Expected: FAIL

- [ ] **Step 3: Реализовать** `bot/handlers/tasks.py`

```python
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from ..keyboards.user import MENU_TASKS, main_menu_kb, task_kb
from ..services.tasks import available_tasks, complete_task, is_channel_member
from ..utils.stars import format_stars

router_tasks = Router()


async def next_task(session, user_id: int, exclude_id: int | None = None):
    tasks = await available_tasks(session, user_id)
    for task in tasks:
        if task.id != exclude_id:
            return task
    return None


def task_text(task) -> str:
    return (
        f"📋 <b>Задание</b>\n\n{task.title}\n\n"
        f"Награда: {format_stars(task.reward_tenths)}"
    )


@router_tasks.callback_query(F.data == MENU_TASKS)
async def show_tasks(callback: CallbackQuery, session) -> None:
    task = await next_task(session, callback.from_user.id)
    if task is None:
        await callback.message.edit_text(
            "📋 Пока нет доступных заданий. Заходи позже!", reply_markup=main_menu_kb()
        )
        await callback.answer()
        return
    await callback.message.edit_text(task_text(task), reply_markup=task_kb(task))
    await callback.answer()


@router_tasks.callback_query(F.data.startswith("task:check:"))
async def check_task(callback: CallbackQuery, session, bot) -> None:
    from ..db.models import TaskItem

    task_id = int(callback.data.split(":")[2])
    task = await session.get(TaskItem, task_id)
    if task is None or not task.active:
        await callback.answer("Задание недоступно.", show_alert=True)
        return

    if task.type == "channel":
        ok = await is_channel_member(bot, task.chat_id or task.url, callback.from_user.id)
        if not ok:
            await callback.answer("❌ Вы ещё не подписались.", show_alert=True)
            return

    done = await complete_task(session, callback.from_user.id, task_id)
    if done is None:
        await callback.answer("Уже выполнено.", show_alert=True)
    else:
        await callback.answer(f"✅ Начислено {format_stars(done.reward_tenths)}")

    nxt = await next_task(session, callback.from_user.id)
    if nxt is None:
        await callback.message.edit_text(
            "📋 Задания закончились! Заходи позже.", reply_markup=main_menu_kb()
        )
    else:
        await callback.message.edit_text(task_text(nxt), reply_markup=task_kb(nxt))


@router_tasks.callback_query(F.data.startswith("task:skip:"))
async def skip_task(callback: CallbackQuery, session) -> None:
    current_id = int(callback.data.split(":")[2])
    nxt = await next_task(session, callback.from_user.id, exclude_id=current_id)
    if nxt is None:
        await callback.answer("Больше заданий нет.", show_alert=True)
        await callback.message.edit_text(
            "📋 Пока нет доступных заданий. Заходи позже!", reply_markup=main_menu_kb()
        )
        return
    await callback.message.edit_text(task_text(nxt), reply_markup=task_kb(nxt))
    await callback.answer()
```

- [ ] **Step 4: Запустить — проходит**

Run: `python -m pytest tests/test_tasks_flow.py -v`
Expected: PASS

- [ ] **Step 5: Коммит**

```bash
git add bot/handlers/tasks.py tests/test_tasks_flow.py
git commit -m "feat: tasks screens with check and skip"
```

---

### Task 15: Обработчик вывода звёзд

**Files:**
- Create: `bot/handlers/withdraw.py`
- Test: `tests/test_withdraw_helpers.py`

**Interfaces:**
- Consumes: `gifts_kb`, `cancel_kb`, `withdraw_admin_kb`, `create_withdrawal`, `GIFTS_BY_ID`.
- Produces: `normalize_username(text: str) -> str | None`; `Router` (`router_withdraw`); FSM state `WithdrawStates.waiting_username`.

- [ ] **Step 1: Написать падающий тест** `tests/test_withdraw_helpers.py`

```python
from bot.handlers.withdraw import normalize_username


def test_normalize_username():
    assert normalize_username("@friend") == "friend"
    assert normalize_username("friend") == "friend"
    assert normalize_username("https://t.me/friend") == "friend"
    assert normalize_username("bad name") is None
    assert normalize_username("") is None
```

- [ ] **Step 2: Запустить — падает**

Run: `python -m pytest tests/test_withdraw_helpers.py -v`
Expected: FAIL

- [ ] **Step 3: Реализовать** `bot/handlers/withdraw.py`

```python
from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ..keyboards.admin import withdraw_admin_kb
from ..keyboards.user import MENU_WITHDRAW, cancel_kb, gifts_kb
from ..services.withdrawals import WithdrawalError, create_withdrawal
from ..utils.gifts import GIFTS_BY_ID
from ..utils.stars import format_stars

router_withdraw = Router()

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{5,32}$")


class WithdrawStates(StatesGroup):
    waiting_username = State()


def normalize_username(text: str) -> str | None:
    text = text.strip()
    if "t.me/" in text:
        text = text.split("t.me/", 1)[1].split("/")[0]
    text = text.lstrip("@")
    if USERNAME_RE.match(text):
        return text
    return None


@router_withdraw.callback_query(F.data == MENU_WITHDRAW)
async def show_gifts(callback: CallbackQuery, session) -> None:
from ..services.referral import count_referrals, get_user

    user = await get_user(session, callback.from_user.id)
    if user.balance_tenths < 150:
        await callback.message.edit_text(
            f"💸 Для вывода нужно минимум 15 ★.\n"
            f"Твой баланс: {format_stars(user.balance_tenths)}.",
            reply_markup=cancel_kb(),
        )
        await callback.answer()
        return
    await callback.message.edit_text(
        f"💸 <b>Вывод звёзд</b>\n\nБаланс: {format_stars(user.balance_tenths)}\n\n"
        "Выбери подарок:",
        reply_markup=gifts_kb(user.balance_tenths),
    )
    await callback.answer()


@router_withdraw.callback_query(F.data.startswith("wd:gift:"))
async def choose_gift(callback: CallbackQuery, state: FSMContext) -> None:
    gift_id = callback.data.split(":")[2]
    gift = GIFTS_BY_ID.get(gift_id)
    if gift is None:
        await callback.answer("Подарок не найден.", show_alert=True)
        return
    await state.update_data(gift_id=gift.id)
    await state.set_state(WithdrawStates.waiting_username)
    await callback.message.edit_text(
        f"🎁 Выбран подарок: {gift.emoji} {gift.name} — {format_stars(gift.stars * 10)}\n\n"
        "Отправь <b>@username</b>, куда вывести звёзды:",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router_withdraw.message(WithdrawStates.waiting_username)
async def receive_username(
    message: Message, state: FSMContext, session, config
) -> None:
    username = normalize_username(message.text or "")
    if username is None:
        await message.answer(
            "❌ Некорректный username. Пример: <code>@username</code>",
            reply_markup=cancel_kb(),
        )
        return

    data = await state.get_data()
    gift = GIFTS_BY_ID.get(data.get("gift_id", ""))
    if gift is None:
        await state.clear()
        await message.answer("Подарок не найден. Начни заново.", reply_markup=cancel_kb())
        return

    try:
        withdrawal = await create_withdrawal(
            session,
            message.from_user.id,
            gift.id,
            gift.name,
            gift.stars,
            username,
        )
    except WithdrawalError as exc:
        await state.clear()
        await message.answer(f"❌ {exc}", reply_markup=cancel_kb())
        return

    await state.clear()

    admin_text = (
        "💸 <b>Новая заявка на вывод</b>\n\n"
        f"🎁 Подарок: {gift.emoji} {gift.name} — {format_stars(gift.stars * 10)}\n"
        f"👤 Заказчик: {message.from_user.full_name} "
        f"(@{message.from_user.username or '—'}, <code>{message.from_user.id}</code>)\n"
        f"📥 Вывести на: @{username}\n"
        f"🕒 Заявка #{withdrawal.id}"
    )
    admin_msg = await message.bot.send_message(
        config.admin_chat_id,
        admin_text,
        reply_markup=withdraw_admin_kb(withdrawal.id, username),
    )
    withdrawal.admin_chat_id = admin_msg.chat.id
    withdrawal.admin_msg_id = admin_msg.message_id
    await session.commit()

    await message.answer(
        "✅ Заявка отправлена! После проверки админ отправит подарок.",
        reply_markup=cancel_kb(),
    )
```

- [ ] **Step 4: Запустить — проходит**

Run: `python -m pytest tests/test_withdraw_helpers.py -v`
Expected: PASS

- [ ] **Step 5: Коммит**

```bash
git add bot/handlers/withdraw.py tests/test_withdraw_helpers.py
git commit -m "feat: withdrawal flow with admin request message"
```

---

### Task 16: Админ-панель

**Files:**
- Create: `bot/handlers/admin.py`
- Test: `tests/test_admin_stats_text.py`

**Interfaces:**
- Consumes: `IsAdmin`, `admin_menu_kb`, `sponsors_admin_kb`, `tasks_admin_kb`, `add_channel_sponsor`, `add_bot_sponsor`, `delete_sponsor`, `active_sponsors`, `get_stats`, `mark_paid`, `Withdrawal`.
- Produces: `stats_text(stats) -> str`; `Router` (`router_admin`); FSM `AdminStates`.

- [ ] **Step 1: Написать падающий тест** `tests/test_admin_stats_text.py`

```python
from bot.handlers.admin import stats_text
from bot.services.stats import Stats


def test_stats_text_contains_month():
    stats = Stats(
        total_users=10,
        new_today=2,
        new_week=5,
        new_month=7,
        referrals=4,
        earned_tenths=300,
        withdrawn_tenths=150,
        pending_withdrawals=1,
        tasks_done=8,
    )
    text = stats_text(stats)
    assert "за месяц" in text.lower()
    assert "10" in text
    assert "30 ★" in text
```

- [ ] **Step 2: Запустить — падает**

Run: `python -m pytest tests/test_admin_stats_text.py -v`
Expected: FAIL

- [ ] **Step 3: Реализовать** `bot/handlers/admin.py`

```python
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ..keyboards.admin import (
    admin_menu_kb,
    sponsors_admin_kb,
    tasks_admin_kb,
)
from ..middlewares.admin_filter import IsAdmin
from ..services.stats import get_stats
from ..services.subscriptions import (
    SponsorError,
    active_sponsors,
    add_bot_sponsor,
    add_channel_sponsor,
    delete_sponsor,
)
from ..services.withdrawals import mark_paid
from ..utils.stars import format_stars

router_admin = Router()


class AdminStates(StatesGroup):
    sponsor_channel_link = State()
    sponsor_bot_link = State()


def stats_text(stats) -> str:
    return (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: {stats.total_users}\n"
        f"🆕 Новых за сегодня: {stats.new_today}\n"
        f"📅 Новых за 7 дней: {stats.new_week}\n"
        f"🗓 Новых за месяц: {stats.new_month}\n"
        f"🤝 Приглашено друзей: {stats.referrals}\n"
        f"💰 Начислено: {format_stars(stats.earned_tenths)}\n"
        f"💸 Выплачено: {format_stars(stats.withdrawn_tenths)}\n"
        f"⏳ Активных заявок: {stats.pending_withdrawals}\n"
        f"✅ Выполнено заданий: {stats.tasks_done}"
    )


@router_admin.message(Command("admin"), IsAdmin)
async def admin_panel(message: Message) -> None:
    await message.answer("🛠 <b>Админ-панель</b>", reply_markup=admin_menu_kb())


@router_admin.callback_query(F.data == "admin:menu", IsAdmin)
async def admin_back(callback: CallbackQuery) -> None:
    await callback.message.edit_text("🛠 <b>Админ-панель</b>", reply_markup=admin_menu_kb())
    await callback.answer()


@router_admin.callback_query(F.data == "admin:stats", IsAdmin)
async def admin_stats(callback: CallbackQuery, session) -> None:
    stats = await get_stats(session)
    await callback.message.edit_text(
        stats_text(stats), reply_markup=admin_menu_kb()
    )
    await callback.answer()


@router_admin.callback_query(F.data == "admin:sponsors", IsAdmin)
async def admin_sponsors(callback: CallbackQuery, session) -> None:
    sponsors = await active_sponsors(session)
    await callback.message.edit_text(
        "📢 <b>Обязательные спонсоры</b>", reply_markup=sponsors_admin_kb(sponsors)
    )
    await callback.answer()


@router_admin.callback_query(F.data == "admin:sponsor:add_channel", IsAdmin)
async def admin_add_channel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.sponsor_channel_link)
    await callback.message.edit_text(
        "Отправь ссылку на канал (@username, t.me/... или id -100...). "
        "Бот должен быть админом в канале.",
        reply_markup=admin_menu_kb(),
    )
    await callback.answer()


@router_admin.message(AdminStates.sponsor_channel_link, IsAdmin)
async def admin_receive_channel(message: Message, state: FSMContext, session, bot) -> None:
    try:
        sponsor = await add_channel_sponsor(session, bot, message.text or "")
    except SponsorError as exc:
        await message.answer(f"❌ {exc}")
        return
    await state.clear()
    await message.answer(
        f"✅ Канал «{sponsor.title}» добавлен в обязательные.",
        reply_markup=admin_menu_kb(),
    )


@router_admin.callback_query(F.data == "admin:sponsor:add_bot", IsAdmin)
async def admin_add_bot(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.sponsor_bot_link)
    await callback.message.edit_text(
        "Отправь ссылку на бота (@username или t.me/...).",
        reply_markup=admin_menu_kb(),
    )
    await callback.answer()


@router_admin.message(AdminStates.sponsor_bot_link, IsAdmin)
async def admin_receive_bot(message: Message, state: FSMContext, session) -> None:
    try:
        sponsor = await add_bot_sponsor(session, message.text or "")
    except SponsorError as exc:
        await message.answer(f"❌ {exc}")
        return
    await state.clear()
    await message.answer(
        f"✅ Бот {sponsor.title} добавлен в обязательные.",
        reply_markup=admin_menu_kb(),
    )


@router_admin.callback_query(F.data.startswith("admin:sponsor:del:"), IsAdmin)
async def admin_del_sponsor(callback: CallbackQuery, session) -> None:
    sponsor_id = int(callback.data.split(":")[3])
    await delete_sponsor(session, sponsor_id)
    sponsors = await active_sponsors(session)
    await callback.message.edit_text(
        "📢 <b>Обязательные спонсоры</b>", reply_markup=sponsors_admin_kb(sponsors)
    )
    await callback.answer("Удалено")


@router_admin.callback_query(F.data == "admin:tasks", IsAdmin)
async def admin_tasks(callback: CallbackQuery, session) -> None:
    from ..db.models import TaskItem
    from sqlalchemy import select

    res = await session.execute(select(TaskItem).order_by(TaskItem.id))
    tasks = list(res.scalars().all())
    await callback.message.edit_text(
        "📋 <b>Задания</b>", reply_markup=tasks_admin_kb(tasks)
    )
    await callback.answer()


@router_admin.callback_query(F.data.startswith("admin:task:del:"), IsAdmin)
async def admin_del_task(callback: CallbackQuery, session) -> None:
    from sqlalchemy import select

    from ..db.models import TaskItem

    task_id = int(callback.data.split(":")[3])
    task = await session.get(TaskItem, task_id)
    if task is not None:
        task.active = False
        await session.commit()
    res = await session.execute(select(TaskItem).where(TaskItem.active.is_(True)))
    tasks = list(res.scalars().all())
    await callback.message.edit_text(
        "📋 <b>Задания</b>", reply_markup=tasks_admin_kb(tasks)
    )
    await callback.answer("Удалено")


@router_admin.callback_query(F.data.startswith("wd:paid:"), IsAdmin)
async def admin_mark_paid(callback: CallbackQuery, session, bot) -> None:
    withdrawal_id = int(callback.data.split(":")[2])
    withdrawal = await mark_paid(session, withdrawal_id)
    if withdrawal is None:
        await callback.answer("Уже выплачено или недостаточно баланса.", show_alert=True)
        return
    try:
        await callback.message.edit_text(
            callback.message.html_text + "\n\n✅ <b>Выплачено</b>"
        )
    except Exception:
        pass
    try:
        await bot.send_message(
            withdrawal.user_id,
            "🎁 Админ отправил вам подарок! Проверьте подарки в Telegram.",
        )
    except Exception:
        pass
    await callback.answer("Отмечено как выплачено")
```

**Примечание:** обработчики добавления заданий и рассылки (`admin:task:add`, `admin:broadcast`) вынесены в отдельную итерацию, чтобы этот таск оставался тестируемым. Минимальная рабочая версия панели (спонсоры, статистика, заявки) закрывается здесь. Добавление заданий и рассылка — Task 16b.

- [ ] **Step 4: Запустить — проходит**

Run: `python -m pytest tests/test_admin_stats_text.py -v`
Expected: PASS

- [ ] **Step 5: Коммит**

```bash
git add bot/handlers/admin.py tests/test_admin_stats_text.py
git commit -m "feat: admin panel (sponsors, stats, withdrawals)"
```

---

### Task 16b: Добавление заданий и рассылка в админ-панели

**Files:**
- Modify: `bot/handlers/admin.py`
- Test: `tests/test_admin_task_add.py`

**Interfaces:**
- Consumes: `TaskItem`, `Broadcast`, `User`, `available_tasks`.
- Produces: `Router` (`router_admin`), FSM states `task_type, task_link, task_title, broadcast_text`.

- [ ] **Step 1: Написать падающий тест** `tests/test_admin_task_add.py`

```python
import pytest

from bot.db.models import TaskItem
from bot.services.tasks import available_tasks


@pytest.mark.asyncio
async def test_added_channel_task_is_available(session):
    from bot.db.models import User

    session.add(User(id=1, username="u", first_name="U"))
    session.add(
        TaskItem(type="channel", title="Подпишись", url="https://t.me/x", chat_id="@x")
    )
    await session.commit()
    assert len(await available_tasks(session, 1)) == 1
```

- [ ] **Step 2: Запустить — проходит сразу (проверка инварианта)**

Run: `python -m pytest tests/test_admin_task_add.py -v`
Expected: PASS

- [ ] **Step 3: Добавить FSM-состояния в** `AdminStates`

```python
    task_type = State()
    task_link = State()
    task_title = State()
    task_reward = State()
    broadcast_text = State()
```

- [ ] **Step 4: Добавить обработчики в** `bot/handlers/admin.py`

```python
TASK_TYPE_LABELS = {"channel": "канал", "bot": "бот"}


@router_admin.callback_query(F.data == "admin:task:add", IsAdmin)
async def admin_task_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.task_type)
    await callback.message.edit_text(
        "Что за задание? Напиши <code>channel</code> (подписка на канал) "
        "или <code>bot</code> (старт в боте).",
        reply_markup=admin_menu_kb(),
    )
    await callback.answer()


@router_admin.message(AdminStates.task_type, IsAdmin)
async def admin_task_type(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip().lower()
    if value not in TASK_TYPE_LABELS:
        await message.answer("Введи channel или bot.")
        return
    await state.update_data(type=value)
    await state.set_state(AdminStates.task_link)
    await message.answer("Отправь ссылку (@username или t.me/...).")


@router_admin.message(AdminStates.task_link, IsAdmin)
async def admin_task_link(message: Message, state: FSMContext) -> None:
    await state.update_data(url=(message.text or "").strip())
    await state.set_state(AdminStates.task_title)
    await message.answer("Отправь название задания.")


@router_admin.message(AdminStates.task_title, IsAdmin)
async def admin_task_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=(message.text or "").strip())
    await state.set_state(AdminStates.task_reward)
    await message.answer("Сколько звёзд за задание? Например 0.5")


@router_admin.message(AdminStates.task_reward, IsAdmin)
async def admin_task_reward(message: Message, state: FSMContext, session) -> None:
    from ..db.models import TaskItem
    from ..utils.stars import stars_to_tenths

    try:
        reward = stars_to_tenths(float((message.text or "").replace(",", ".")))
    except ValueError:
        await message.answer("Введи число, например 0.5")
        return

    data = await state.get_data()
    from ..services.subscriptions import parse_chat_ref

    try:
        chat_ref = parse_chat_ref(data["url"])
    except SponsorError as exc:
        await state.clear()
        await message.answer(f"❌ {exc}", reply_markup=admin_menu_kb())
        return

    task = TaskItem(
        type=data["type"],
        title=data["title"],
        url=data["url"],
        chat_id=chat_ref if data["type"] == "channel" else None,
        reward_tenths=reward,
    )
    session.add(task)
    await session.commit()
    await state.clear()
    await message.answer(
        f"✅ Задание «{task.title}» добавлено.", reply_markup=admin_menu_kb()
    )


@router_admin.callback_query(F.data == "admin:broadcast", IsAdmin)
async def admin_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.broadcast_text)
    await callback.message.edit_text(
        "Отправь текст рассылки.", reply_markup=admin_menu_kb()
    )
    await callback.answer()


@router_admin.message(AdminStates.broadcast_text, IsAdmin)
async def admin_broadcast_send(message: Message, state: FSMContext, session, bot) -> None:
    from sqlalchemy import select

    from ..db.models import Broadcast, User

    await state.clear()
    res = await session.execute(select(User.id).where(User.is_blocked.is_(False)))
    user_ids = list(res.scalars().all())
    sent = failed = 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, message.text or "")
            sent += 1
        except Exception:
            failed += 1
    session.add(Broadcast(text=message.text or "", sent_count=sent, failed_count=failed))
    await session.commit()
    await message.answer(
        f"✅ Рассылка завершена. Доставлено: {sent}, ошибок: {failed}.",
        reply_markup=admin_menu_kb(),
    )
```

- [ ] **Step 5: Запустить тест**

Run: `python -m pytest tests/test_admin_task_add.py -v`
Expected: PASS

- [ ] **Step 6: Коммит**

```bash
git add bot/handlers/admin.py tests/test_admin_task_add.py
git commit -m "feat: admin task creation and broadcast"
```

---

### Task 17: Сборка, запуск и документация

**Files:**
- Create: `bot/main.py`, `run.py`, `README.md`
- Test: `tests/test_app_wiring.py`

**Interfaces:**
- Consumes: всё выше.
- Produces: `build_dispatcher(config, session_factory) -> Dispatcher`; `main()`.

- [ ] **Step 1: Написать падающий тест** `tests/test_app_wiring.py`

```python
from bot.config import Config
from bot.main import build_dispatcher


def _config():
    return Config(
        bot_token="1:x",
        admin_ids=(1,),
        admin_chat_id=-100,
        support_url="https://t.me/s",
        partner_api_key="k",
        db_path=":memory:",
        partner_api_host="127.0.0.1",
        partner_api_port=8080,
    )


async def test_build_dispatcher_registers_routers(engine):
    from bot.db.session import make_session_factory

    dp = build_dispatcher(_config(), make_session_factory(engine))
    assert dp is not None
    assert dp.workflow_data["support_url"] == "https://t.me/s"
```

- [ ] **Step 2: Запустить — падает**

Run: `python -m pytest tests/test_app_wiring.py -v`
Expected: FAIL

- [ ] **Step 3: Реализовать** `bot/main.py`

```python
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web

from .config import Config, load_config
from .db.session import create_engine, init_db, make_session_factory
from .handlers.admin import router_admin
from .handlers.start import router_start
from .handlers.tasks import router_tasks
from .handlers.user import router_user
from .handlers.withdraw import router_withdraw
from .middlewares.db import DbSessionMiddleware
from .middlewares.subscription import SubscriptionMiddleware
from .services.partner_api import create_partner_app

logging.basicConfig(level=logging.INFO)


def build_dispatcher(config: Config, session_factory) -> Dispatcher:
    dp = Dispatcher()
    for observer in (dp.message, dp.callback_query):
        observer.middleware(DbSessionMiddleware(session_factory))
        observer.middleware(SubscriptionMiddleware(config.admin_ids))

    dp.workflow_data["support_url"] = config.support_url
    dp.workflow_data["config"] = config

    dp.include_router(router_admin)
    dp.include_router(router_start)
    dp.include_router(router_user)
    dp.include_router(router_tasks)
    dp.include_router(router_withdraw)
    return dp


async def main() -> None:
    config = load_config()
    engine = create_engine(config.db_path)
    await init_db(engine)
    session_factory = make_session_factory(engine)

    bot = Bot(
        config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = build_dispatcher(config, session_factory)

    app = create_partner_app(session_factory, config.partner_api_key)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.partner_api_host, config.partner_api_port)
    await site.start()

    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
```

`support_url` и `config` кладутся в `dp.workflow_data`, поэтому приходят в хендлеры `show_instruction` и `receive_username` как именованные аргументы.

- [ ] **Step 4: Создать** `run.py`

```python
import asyncio

from bot.main import main

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 5: Создать** `README.md`

```markdown
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
```

- [ ] **Step 6: Запустить все тесты**

Run: `python -m pytest -v`
Expected: все тесты PASS

- [ ] **Step 7: Ручная проверка запуска**

1. Заполнить `.env`.
2. `python run.py`.
3. В Telegram: `/start`, пройти спонсоров, открыть все разделы меню, проверить «Назад».
4. `/admin` — добавить спонсора, задание, посмотреть статистику, сделать рассылку.
5. Создать вывод, нажать «Выплачено» в админ-чате, проверить уведомление пользователю.

- [ ] **Step 8: Коммит**

```bash
git add bot/main.py run.py README.md tests/test_app_wiring.py
git commit -m "feat: wire dispatcher, aiohttp partner server and docs"
```

---

## Самопроверка плана

- **Покрытие спецификации:** конфиг (§7) — Task 1; модели (§3) — Task 2; реферал (§4.1) — Tasks 4, 12; спонсоры каналы+боты, добавление по ссылке с проверкой админа (§5) — Task 5; меню/профиль/инструкция/заработать (§4.2) — Tasks 10, 13; задания + пропуск (§4.3) — Tasks 6, 14; вывод + чат заявок + кнопки профиль/выплачено (§4.4) — Tasks 7, 10, 15, 16; админ-панель, статистика за месяц, рассылка (§5) — Tasks 8, 16, 16b; партнёрская интеграция (§6) — Task 9; тесты (§8) — во всех тасках; структура — Tasks 1–17.
- **Плейсхолдеры:** не найдено. Все шаги содержат реальный код и команды; `count_referrals` определена в Task 4 и используется в Task 13.
- **Согласованность имён:** `TaskItem` (не `Task`), `REFERRAL_REWARD_TENTHS`, `format_stars`, `GIFTS_BY_ID`, `create_withdrawal`/`mark_paid`, `available_tasks`/`complete_task`, `missing_sponsors`, `parse_chat_ref`, `build_dispatcher` — используются одинаково во всех тасках.
- **Ограничения:** tenths — везде; один друг/спонсор/задание — уникальность в Tasks 4, 5, 6.
```
