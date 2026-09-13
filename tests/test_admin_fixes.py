import pytest

from bot.db.models import TaskItem, User
from bot.handlers import admin as admin_handlers
from bot.services.partners import create_partner
from bot.services.promos import create_promo, list_promos
from tests.fakes import FakeBot, FakeChat


class FakeMessage:
    def __init__(self, text=""):
        self.text = text
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

    await admin_handlers._finish_task(FakeBot(), message, state, session, None)

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
async def test_sponsor_type_channel_asks_subtype():
    callback = FakeCallback("admin:sponsor:type:channel")
    state = FakeState()

    await admin_handlers.admin_sponsor_type(callback, state)

    assert (await state.get_data())["type"] == "channel"
    assert state.state == admin_handlers.AdminStates.sponsor_subtype
    assert callback.message.answers
    assert callback.answered is True


@pytest.mark.asyncio
async def test_sponsor_subtype_stores_and_asks_link():
    callback = FakeCallback("admin:sponsor:subtype:private_request")
    state = FakeState({"type": "channel"})

    await admin_handlers.admin_sponsor_subtype(callback, state)

    data = await state.get_data()
    assert data["subtype"] == "private_request"
    assert data["type"] == "channel"
    assert state.state == admin_handlers.AdminStates.sponsor_link
    assert callback.message.answers
    assert callback.answered is True


@pytest.mark.asyncio
async def test_admin_promo_uses_creates_promo(session):
    message = FakeMessage("10")
    state = FakeState({"code": "SALE", "stars": 5})

    await admin_handlers.admin_promo_uses(message, state, session)

    assert state.cleared is True
    assert message.answers
    assert "SALE" in message.answers[-1][0]
    promos = await list_promos(session)
    assert [p.code for p in promos] == ["SALE"]


@pytest.mark.asyncio
async def test_admin_promo_uses_duplicate_code_resets_to_code_state(session):
    await create_promo(session, "SALE", 5, 0)
    message = FakeMessage("10")
    state = FakeState({"code": "SALE", "stars": 5})

    await admin_handlers.admin_promo_uses(message, state, session)

    assert state.state == admin_handlers.AdminStates.promo_code
    assert message.answers
    assert "заново" in message.answers[-1][0]
    assert len(await list_promos(session)) == 1


@pytest.mark.asyncio
async def test_admin_promo_del_removes_promo(session):
    promo = await create_promo(session, "TMP", 1, 0)
    callback = FakeCallback(f"admin:promo:del:{promo.id}")

    await admin_handlers.admin_promo_del(callback, session)

    assert await list_promos(session) == []
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


@pytest.mark.asyncio
async def test_task_type_channel_asks_subtype():
    callback = FakeCallback("admin:task:type:channel")
    state = FakeState()

    await admin_handlers.admin_task_type(callback, state)

    assert (await state.get_data())["type"] == "channel"
    assert state.state == admin_handlers.AdminStates.task_subtype
    assert callback.message.answers
    assert callback.answered is True


@pytest.mark.asyncio
async def test_admin_del_task_hard_deletes(session):
    task = TaskItem(type="channel", title="T", url="u", chat_id="@t")
    session.add(task)
    await session.commit()
    task_id = task.id
    callback = FakeCallback(f"admin:task:del:{task_id}")

    await admin_handlers.admin_del_task(callback, session)

    assert await session.get(TaskItem, task_id) is None
    assert callback.message.answers
    assert callback.answered is True


@pytest.mark.asyncio
async def test_admin_reset_user_zeroes_balance_only(session):
    user = User(id=555, balance_tenths=50, total_earned_tenths=120)
    session.add(user)
    await session.commit()

    message = FakeMessage("555")
    state = FakeState()

    await admin_handlers.admin_reset_user(message, state, session)

    assert user.balance_tenths == 0
    assert user.total_earned_tenths == 120
    assert state.cleared is True
    assert message.answers
    assert "обнулены" in message.answers[-1][0]


@pytest.mark.asyncio
async def test_admin_reset_user_unknown_id_answers_error(session):
    message = FakeMessage("999999")
    state = FakeState()

    await admin_handlers.admin_reset_user(message, state, session)

    assert message.answers
    assert "не найден" in message.answers[-1][0]
    assert state.cleared is False
