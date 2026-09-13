from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GiftSpec:
    id: str
    name: str
    emoji: str
    stars: int


FIXED_GIFTS: tuple[GiftSpec, ...] = (
    GiftSpec("bear", "Медвежонок", "🧸", 15),
    GiftSpec("heart", "Сердце", "💖", 15),
    GiftSpec("rose", "Роза", "🌹", 25),
    GiftSpec("gift", "Подарок", "🎁", 25),
    GiftSpec("bouquet", "Букет", "💐", 50),
    GiftSpec("cake", "Тортик", "🎂", 50),
    GiftSpec("rocket", "Ракета", "🚀", 50),
    GiftSpec("cup", "Кубок", "🏆", 100),
    GiftSpec("ring", "Кольцо", "💍", 100),
    GiftSpec("diamond", "Алмаз", "💎", 100),
)

GIFTS_BY_ID: dict[str, GiftSpec] = {gift.id: gift for gift in FIXED_GIFTS}
