import pytest

from bot.utils.assets import replace_screen


class FakeMessage:
    def __init__(self, raise_on_delete=False):
        self.raise_on_delete = raise_on_delete
        self.deleted = False
        self.answers = []

    async def delete(self):
        if self.raise_on_delete:
            raise RuntimeError("cannot delete")
        self.deleted = True

    async def answer(self, text, reply_markup=None):
        self.answers.append((text, reply_markup))

    async def answer_photo(self, photo, caption=None, reply_markup=None):
        self.answers.append((caption, reply_markup))


class FakeCallback:
    def __init__(self, raise_on_delete=False):
        self.message = FakeMessage(raise_on_delete=raise_on_delete)


@pytest.mark.asyncio
async def test_replace_screen_deletes_old_and_sends_new():
    callback = FakeCallback()

    await replace_screen(callback, "hi")

    assert callback.message.deleted is True
    assert len(callback.message.answers) == 1
    assert callback.message.answers[0][0] == "hi"


@pytest.mark.asyncio
async def test_replace_screen_sends_even_if_delete_fails():
    callback = FakeCallback(raise_on_delete=True)

    await replace_screen(callback, "hi")

    assert callback.message.deleted is False
    assert len(callback.message.answers) == 1
    assert callback.message.answers[0][0] == "hi"
