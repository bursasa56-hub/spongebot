import pytest

from bot.db.models import User
from bot.handlers.withdraw import show_gifts


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

    async def answer(self, text=None, show_alert=False):
        self.answers.append((text, show_alert))


class FakeState:
    def __init__(self, data=None):
        self.data = dict(data or {})

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def get_data(self):
        return dict(self.data)


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
async def test_show_gifts_blocks_without_five_friends(session):
    session.add(User(id=1, username="u", first_name="U", balance_tenths=200))
    await session.commit()
    callback = FakeCallback(user_id=1)

    await show_gifts(callback, FakeState(), session)

    text, markup = _last_sent(callback)
    assert "5" in text
    callbacks = _callbacks(markup)
    assert not any(c.startswith("wd:gift:") for c in callbacks)


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
