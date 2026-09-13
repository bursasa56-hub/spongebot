from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ..utils.gifts import FIXED_GIFTS
from .models import Base, Gift


def ensure_db_dir(db_path: str) -> None:
    if db_path == ":memory:":
        return
    from pathlib import Path

    parent = Path(db_path).parent
    if str(parent):
        parent.mkdir(parents=True, exist_ok=True)


def normalize_database_url(database_url: str) -> tuple[str, dict]:
    """Return (async SQLAlchemy URL, connect_args) for a Postgres URL."""
    url = database_url.strip()
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]

    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    connect_args: dict = {}
    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)
    if sslmode and sslmode != "disable":
        connect_args["ssl"] = True
    clean = urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
    return clean, connect_args


def create_engine(db_path: str, database_url: str | None = None) -> AsyncEngine:
    if database_url:
        url, connect_args = normalize_database_url(database_url)
        return create_async_engine(url, echo=False, connect_args=connect_args, pool_pre_ping=True)
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
