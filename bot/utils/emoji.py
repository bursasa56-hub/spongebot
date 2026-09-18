from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

DEFAULT_SET = "vector_icons_by_fStikBot"

# fallback emoji -> custom_emoji_id
EMOJI_IDS: dict[str, str] = {}


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
    if not text or not EMOJI_IDS:
        return text or ""
    result = text
    for emoji, custom_id in EMOJI_IDS.items():
        if emoji in result:
            result = re.sub(
                re.escape(emoji) + r"(?!</tg-emoji>)",
                f'<tg-emoji emoji-id="{custom_id}">{emoji}</tg-emoji>',
                result,
            )
    return result
