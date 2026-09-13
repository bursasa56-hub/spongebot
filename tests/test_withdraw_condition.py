import pytest

from bot.db.models import User
from bot.handlers.withdraw import WithdrawStates, choose_gift, show_gifts


class FakeMessage:
    def __init__(self):
        self.answers = []
        self.photos = []

    async def answer(self, text, reply_markup=None, **kwargs):
        self.answers.append((text, reply_markup))

    async def answer_photo(self, photo, caption=None, reply_markup=None, **kwargs):
        self.photos.append((photo, caption, reply_markup))


class FakeCallback:
    def __init__(self, data="menu:withdraw", user_id=1):
        self.data = data
        self.from_user = type("U", (), {"id": user_id})()
        self.message = FakeMessage()
        self.answers = []
        self.answered = False

    async def answer(self, text=None, show_alert=False):
        self.answers.append((text, show_alert))
        self.answered = True


class FakeState:
    def __init__(self, data=None):
        self.data = dict(data or {})
        self.state = None

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def get_data(self):
        return dict(self.data)

    async def set_state(self, state):
        self.state = state

    async def get_state(self):
        return self.state


def _last_sent(callback):
    msg = callback.message
    if msg.photos:
        _, caption, markup = msg.photos[-1]
        return caption, markup
    text, markup = msg.answers[-1]
    return text, markup


def _callbacks(markup):
    return [b.callback_data for row in markup.inline_keyboard for b in row]


@pytest.mark.asyncio
async def test_show_gifts_shows_grid_without_five_friends(session):
    session.add(User(id=1, username="u", first_name="U", balance_tenths=200))
    await session.commit()
    callback = FakeCallback(user_id=1)

    await show_gifts(callback, FakeState(), session)

    text, markup = _last_sent(callback)
    assert "5" in text
    callbacks = _callbacks(markup)
    assert "wd:gift:bear" in callbacks


@pytest.mark.asyncio
async def test_choose_gift_alerts_without_five_friends(session):
    session.add(User(id=1, username="u", first_name="U", balance_tenths=200))
    await session.commit()
    callback = FakeCallback(data="wd:gift:bear", user_id=1)
    state = FakeState()

    await choose_gift(callback, state, session)

    assert callback.answered is True
    alert_text, show_alert = callback.answers[-1]
    assert show_alert is True
    assert alert_text == "❌ Для вывода нужно пригласить минимум 5 друзей."
    assert await state.get_state() is None


@pytest.mark.asyncio
async def test_choose_gift_advances_with_five_friends_and_balance(session):
    session.add(User(id=1, username="u", first_name="U", balance_tenths=200))
    for uid in range(2, 7):
        session.add(
            User(id=uid, username=f"f{uid}", first_name="F", referred_by=1)
        )
    await session.commit()
    callback = FakeCallback(data="wd:gift:bear", user_id=1)
    state = FakeState()

    await choose_gift(callback, state, session)

    assert await state.get_state() == WithdrawStates.waiting_username


@pytest.mark.asyncio
async def test_show_gifts_shows_grid_with_five_friends(session):
    session.add(User(id=1, username="u", first_name="U", balance_tenths=200))
    for uid in range(2, 7):
        session.add(
            User(id=uid, username=f"f{uid}", first_name="F", referred_by=1)
        )
    await session.commit()
    callback = FakeCallback(user_id=1)

    await show_gifts(callback, FakeState(), session)

    _, markup = _last_sent(callback)
    assert "wd:gift:bear" in _callbacks(markup)


@pytest.mark.asyncio
async def test_show_gifts_resets_to_friend_flag(session):
    session.add(User(id=1, username="u", first_name="U", balance_tenths=200))
    for uid in range(2, 7):
        session.add(
            User(id=uid, username=f"f{uid}", first_name="F", referred_by=1)
        )
    await session.commit()
    callback = FakeCallback(user_id=1)
    state = FakeState({"to_friend": True})

    await show_gifts(callback, state, session)

    assert await state.get_data() == {"to_friend": False}
