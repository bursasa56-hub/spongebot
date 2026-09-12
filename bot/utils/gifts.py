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
    GiftSpec("rabbit", "Плюшевый заяц", "🐰", 20),
    GiftSpec("rose", "Роза", "🌹", 25),
    GiftSpec("heart", "Сердце", "❤️", 30),
    GiftSpec("cake", "Тортик", "🎂", 35),
    GiftSpec("ring", "Кольцо", "💍", 40),
    GiftSpec("bouquet", "Букет", "💐", 50),
    GiftSpec("crown", "Корона", "👑", 60),
    GiftSpec("cup", "Кубок", "🏆", 75),
    GiftSpec("diamond", "Алмаз", "💎", 100),
)

GIFTS_BY_ID: dict[str, GiftSpec] = {gift.id: gift for gift in FIXED_GIFTS}
