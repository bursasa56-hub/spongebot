import pytest

from bot.db.models import User
from bot.handlers.start import _credit_and_notify, parse_ref


def test_parse_ref():
    assert parse_ref("ref_123") == 123
    assert parse_ref("/start ref_5") == 5
    assert parse_ref(None) is None
    assert parse_ref("garbage") is None
    assert parse_ref("ref_abc") is None


class _FakeBot:
    async def send_message(self, *args, **kwargs):
        pass


@pytest.mark.asyncio
async def test_credit_and_notify_marks_subscribed(session):
    session.add(User(id=1, username="u", first_name="U"))
    await session.commit()

    await _credit_and_notify(session, _FakeBot(), 1)

    user = await session.get(User, 1)
    assert user.subscribed is True
