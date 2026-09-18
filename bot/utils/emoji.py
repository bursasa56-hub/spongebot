from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

DEFAULT_SET = "vector_icons_by_fStikBot"

# fallback emoji -> custom_emoji_id (auto-loaded from the pack)
EMOJI_IDS: dict[str, str] = {}

# Our UI emoji -> chosen custom_emoji_id from the pack (takes priority over EMOJI_IDS).
OVERRIDES: dict[str, str] = {
    "👋": "5339286072876614251",  # hand
    "💰": "5237761614458933049",  # coin
    "💵": "5237761614458933049",  # coin
    "🎁": "5258212320282168974",  # balloon
    "🎟": "5454386656628991407",  # key
    "📖": "5258466217273871977",  # idea
    "📋": "5341492148468465410",  # folder
    "👤": "5454371323595744068",  # face
    "👥": "5454365405130810498",  # hearts
    "💸": "5258296359907249075",  # currency
    "🎮": "5235588635885054955",  # dice
    "🆘": "5453965363286925977",  # phone
    "🔒": "5393302369024882368",  # lock
    "✅": "5219899949281453881",  # check
    "⭐": "5310224206732996002",  # star
    "💎": "5264892613630111886",  # diamond
    "⚡": "5219943216781995020",  # lightning
    "🔥": "5222148368955877900",  # fire
    "❗": "5220197908342648622",  # exclamation
    "📈": "5246794802560774143",  # top
    "🔗": "5454419255430767770",  # paperclip
    "🎉": "5454345339043601366",  # fireworks
    "🤖": "5314413943035278948",  # brain
    "🆔": "5454079785510660283",  # laptop
}


def _mapping() -> dict[str, str]:
    return {**EMOJI_IDS, **OVERRIDES}


async def load_custom_emoji(bot, set_name: str = DEFAULT_SET) -> int:
    """Fetch the custom emoji set and build the fallback-emoji -> custom_emoji_id map."""
    try:
        sticker_set = await bot.get_sticker_set(set_name)
    except Exception:
        logger.exception("Could not load custom emoji set %s", set_name)
        return 0
    count = 0
    for sticker in sticker_set.stickers:
        custom_id = getattr(sticker, "custom_emoji_id", None)
        emoji = getattr(sticker, "emoji", None)
        if custom_id and emoji:
            EMOJI_IDS[emoji] = custom_id
            count += 1
    logger.info("Loaded %s custom emoji from %s", count, set_name)
    return count


def render(text: str | None) -> str:
    """Replace known emoji in the text with <tg-emoji> markup (falls back to the plain emoji).

    Already-rendered emoji are left untouched, so calling render twice is safe
    (handlers may wrap a text that send_screen also renders).
    """
    mapping = _mapping()
    if not text or not mapping:
        return text or ""
    result = text
    for emoji, custom_id in mapping.items():
        if emoji in result:
            result = re.sub(
                re.escape(emoji) + r"(?!</tg-emoji>)",
                f'<tg-emoji emoji-id="{custom_id}">{emoji}</tg-emoji>',
                result,
            )
    return result
