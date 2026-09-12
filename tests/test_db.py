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
