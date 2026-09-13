from __future__ import annotations

import random

EMOJIS = ("🍎", "🍌", "🍇", "🍒", "🍓", "🍍", "🥝", "🍑", "🍉", "🥥")


def build_captcha(count: int = 4) -> tuple[str, list[str]]:
    options = random.sample(list(EMOJIS), count)
    target = random.choice(options)
    return target, options
