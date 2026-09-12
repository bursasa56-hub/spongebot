from __future__ import annotations

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
