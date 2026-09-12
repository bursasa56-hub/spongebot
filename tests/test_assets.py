import pytest

from bot.utils import assets
from bot.utils.assets import asset_path, send_screen


def test_asset_path_missing_is_none():
    assert asset_path("__missing__") is None


def test_asset_path_finds_png(tmp_path, monkeypatch):
    monkeypatch.setattr(assets, "ASSETS_DIR", tmp_path)
    (tmp_path / "menu.png").write_bytes(b"x")
    assert asset_path("menu") == tmp_path / "menu.png"


class FakeMessage:
    def __init__(self):
        self.answers = []
        self.photos = []

    async def answer(self, text, reply_markup=None):
        self.answers.append((text, reply_markup))

    async def answer_photo(self, photo, caption=None, reply_markup=None):
        self.photos.append((photo, caption, reply_markup))


@pytest.mark.asyncio
async def test_send_screen_falls_back_to_text():
    message = FakeMessage()
    await send_screen(message, "hello", asset="__missing__")
    assert len(message.answers) == 1
    assert len(message.photos) == 0


@pytest.mark.asyncio
async def test_send_screen_no_asset_uses_text():
    message = FakeMessage()
    await send_screen(message, "hello")
    assert len(message.answers) == 1
    assert len(message.photos) == 0


@pytest.mark.asyncio
async def test_send_screen_uses_photo_when_present(tmp_path, monkeypatch):
    monkeypatch.setattr(assets, "ASSETS_DIR", tmp_path)
    (tmp_path / "menu.png").write_bytes(b"x")
    message = FakeMessage()
    await send_screen(message, "hello", asset="menu")
    assert len(message.answers) == 0
    assert len(message.photos) == 1
