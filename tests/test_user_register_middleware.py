from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from bot.db.models import User
from bot.middlewares.user import UserRegisterMiddleware
from bot.services.referral import register_user


def _event(user_id=42, username="u", first_name="U", is_bot=False):
    user = SimpleNamespace(
        id=user_id, username=username, first_name=first_name, is_bot=is_bot
    )
    return SimpleNamespace(from_user=user)


async def _handler(event, data):
    return "handled"


@pytest.mark.asyncio
async def test_registers_user_on_event(session):
    middleware = UserRegisterMiddleware()
    result = await middleware(_handler, _event(), {"session": session})
    assert result == "handled"

    user = await session.get(User, 42)
    assert user is not None
    assert user.username == "u"
    assert user.first_name == "U"


@pytest.mark.asyncio
async def test_updates_existing_user_without_duplicating(session):
    await register_user(session, 1, "owner", "Owner")
    await register_user(session, 42, "old", "Old", ref_id=1)

    middleware = UserRegisterMiddleware()
    await middleware(_handler, _event(username="new", first_name="New"), {"session": session})

    user = await session.get(User, 42)
    assert user.username == "new"
    assert user.first_name == "New"
    assert user.referred_by == 1

    count = (
        await session.execute(
            select(func.count()).select_from(User).where(User.id == 42)
        )
    ).scalar_one()
    assert count == 1
