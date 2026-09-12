import pytest

from bot.handlers import admin as admin_handlers
from bot.services.partners import create_partner
from tests.fakes import FakeBot, FakeChat


class FakeMessage:
    def __init__(self):
        self.answers = []
        self.edits = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))

    async def edit_text(self, text, **kwargs):
        self.edits.append((text, kwargs))


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


class FakeCallback:
    def __init__(self, data=""):
        self.data = data
        self.message = FakeMessage()
        self.answered = False

    async def answer(self, *args, **kwargs):
        self.answered = True


@pytest.mark.asyncio
async def test_finish_task_escapes_title(session):
    state = FakeState(
        {"type": "channel", "url": "@chan", "title": "<b>Evil</b>", "reward": 5}
    )
    message = FakeMessage()

    await admin_handlers._finish_task(message, state, session, None)

    text = message.answers[-1][0]
    assert "&lt;b&gt;Evil&lt;/b&gt;" in text
    assert "<b>Evil</b>" not in text
    assert state.cleared is True


@pytest.mark.asyncio
async def test_admin_back_clears_state():
    callback = FakeCallback("admin:menu")
    state = FakeState()

    await admin_handlers.admin_back(callback, state)

    assert state.cleared is True
    assert callback.message.answers
    assert not callback.message.edits
    assert callback.answered is True


@pytest.mark.asyncio
async def test_admin_partner_key_sends_key(session):
    partner = await create_partner(session, "Acme")
    callback = FakeCallback(f"admin:partner:key:{partner.id}")

    await admin_handlers.admin_partner_key(callback, session)

    text = callback.message.answers[-1][0]
    assert partner.api_key in text
    assert "<code>" in text
    assert callback.answered is True


@pytest.mark.asyncio
async def test_sponsor_type_channel_stores_type_and_asks_link():
    callback = FakeCallback("admin:sponsor:type:channel")
    state = FakeState()

    await admin_handlers.admin_sponsor_type(callback, state)

    assert (await state.get_data())["type"] == "channel"
    assert state.state == admin_handlers.AdminStates.sponsor_link
    assert callback.message.answers
    assert callback.answered is True


@pytest.mark.asyncio
async def test_sponsor_duration_one_sets_hours_state():
    callback = FakeCallback("admin:sponsor:duration:1")
    state = FakeState({"type": "channel", "link": "@chan"})

    await admin_handlers.admin_sponsor_duration(callback, state)

    assert state.state == admin_handlers.AdminStates.sponsor_hours
    assert callback.answered is True


@pytest.mark.asyncio
async def test_sponsor_quota_zero_finishes_channel(session):
    bot = FakeBot(member_status="administrator", chat=FakeChat(-100, "Chan", "chan"))
    callback = FakeCallback("admin:sponsor:quota:0")
    state = FakeState({"type": "channel", "link": "@chan", "hours": 0})

    await admin_handlers.admin_sponsor_quota_choice(callback, state, session, bot)

    assert state.cleared is True
    assert callback.message.answers
    assert "добавлен" in callback.message.answers[-1][0]
    assert callback.answered is True


@pytest.mark.asyncio
async def test_task_type_bot_stores_type_and_asks_link():
    callback = FakeCallback("admin:task:type:bot")
    state = FakeState()

    await admin_handlers.admin_task_type(callback, state)

    assert (await state.get_data())["type"] == "bot"
    assert state.state == admin_handlers.AdminStates.task_link
    assert callback.message.answers
    assert callback.answered is True
