import pytest

from bot.db.models import TaskItem
from bot.services.tasks import self_verifiable
from tests.fakes import FakeBot


@pytest.mark.asyncio
async def test_bot_task_is_never_self_verifiable():
    task = TaskItem(id=1, type="bot", title="B", url="https://t.me/b")
    bot = FakeBot(member_status="member")
    assert await self_verifiable(bot, task, 1) is False
    assert bot.member_calls == []


@pytest.mark.asyncio
async def test_channel_task_verifies_membership():
    task = TaskItem(id=2, type="channel", title="C", url="https://t.me/c", chat_id="@c")

    member = FakeBot(member_status="member")
    assert await self_verifiable(member, task, 1) is True
    assert member.member_calls == [("@c", 1)]

    outsider = FakeBot(member_status="left")
    assert await self_verifiable(outsider, task, 1) is False
    assert outsider.member_calls == [("@c", 1)]
