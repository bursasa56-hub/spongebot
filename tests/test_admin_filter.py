import pytest

from bot.middlewares.admin_filter import IsAdmin


class FakeUser:
    def __init__(self, uid):
        self.id = uid


class FakeEvent:
    def __init__(self, uid):
        self.from_user = FakeUser(uid)


@pytest.mark.asyncio
async def test_is_admin_filter():
    f = IsAdmin()
    assert await f(FakeEvent(1), admin_ids={1}) is True
    assert await f(FakeEvent(2), admin_ids={1}) is False
    assert await f(FakeEvent(2), admin_ids=None) is False
