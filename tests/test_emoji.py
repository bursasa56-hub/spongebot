import pytest

from bot.utils import emoji
from bot.utils.emoji import load_custom_emoji, render


def test_render_no_map_returns_text(monkeypatch):
    monkeypatch.setattr(emoji, "EMOJI_IDS", {})
    monkeypatch.setattr(emoji, "OVERRIDES", {})
    assert render("hi") == "hi"
    assert render(None) == ""


def test_render_replaces_known_emoji(monkeypatch):
    monkeypatch.setattr(emoji, "EMOJI_IDS", {"⭐": "123"})
    monkeypatch.setattr(emoji, "OVERRIDES", {})
    assert render("a ⭐ b") == 'a <tg-emoji emoji-id="123">⭐</tg-emoji> b'


def test_render_overrides_priority(monkeypatch):
    monkeypatch.setattr(emoji, "EMOJI_IDS", {"⭐": "auto"})
    monkeypatch.setattr(emoji, "OVERRIDES", {"⭐": "manual"})
    assert render("⭐") == '<tg-emoji emoji-id="manual">⭐</tg-emoji>'


def test_render_is_idempotent(monkeypatch):
    monkeypatch.setattr(emoji, "EMOJI_IDS", {"⭐": "123"})
    monkeypatch.setattr(emoji, "OVERRIDES", {})
    once = render("a ⭐ b")
    assert render(once) == once


class FakeSticker:
    def __init__(self, emoji=None, custom_emoji_id=None):
        self.emoji = emoji
        self.custom_emoji_id = custom_emoji_id


class FakeStickerSet:
    def __init__(self, stickers):
        self.stickers = stickers


class FakeBot:
    def __init__(self, sticker_set=None, raise_error=False):
        self._sticker_set = sticker_set
        self._raise_error = raise_error

    async def get_sticker_set(self, name):
        if self._raise_error:
            raise RuntimeError("no set")
        return self._sticker_set


@pytest.mark.asyncio
async def test_load_custom_emoji_builds_map(monkeypatch):
    monkeypatch.setattr(emoji, "EMOJI_IDS", {})
    bot = FakeBot(
        FakeStickerSet(
            [
                FakeSticker(emoji="⭐", custom_emoji_id="123"),
                FakeSticker(emoji="🔥", custom_emoji_id=None),
                FakeSticker(emoji=None, custom_emoji_id="999"),
            ]
        )
    )
    count = await load_custom_emoji(bot)
    assert count == 1
    assert emoji.EMOJI_IDS == {"⭐": "123"}


@pytest.mark.asyncio
async def test_load_custom_emoji_error_leaves_map_empty(monkeypatch):
    monkeypatch.setattr(emoji, "EMOJI_IDS", {})
    count = await load_custom_emoji(FakeBot(raise_error=True))
    assert count == 0
    assert emoji.EMOJI_IDS == {}
