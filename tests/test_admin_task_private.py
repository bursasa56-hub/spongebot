import pytest
from sqlalchemy import select

from bot.db.models import TaskItem
from bot.handlers import admin as admin_handlers
from tests.fakes import FakeBot, FakeChat


class FakeMessage:
    def __init__(self, text=""):
        self.text = text
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))


class FakeState:
    def __init__(self, data=None):
        self.data = data or {}
        self.cleared = False
        self.state = None

    async def get_data(self):
        return dict(self.data)

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def set_state(self, state):
        self.state = state

    async def clear(self):
        self.cleared = True
        self.data = {}


@pytest.mark.asyncio
async def test_finish_task_private_request_creates_invite(session):
    bot = FakeBot(
        id=999,
        chat=FakeChat(-100, "Chan", None),
        member_status="administrator",
        invite_link="https://t.me/+abc",
    )
    state = FakeState(
        {
            "type": "channel",
            "subtype": "private_request",
            "url": "-100",
            "title": "T",
            "reward": 5,
        }
    )
    message = FakeMessage()

    await admin_handlers._finish_task(bot, message, state, session, None)

    res = await session.execute(select(TaskItem))
    task = res.scalar_one()
    assert task.subtype == "private_request"
    assert task.chat_id == "-100"
    assert task.url == "https://t.me/+abc"
    assert bot.invite_calls == [(-100, True)]
    assert state.cleared is True
    assert message.answers
