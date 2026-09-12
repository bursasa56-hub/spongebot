from __future__ import annotations


def format_stars(tenths: int) -> str:
    if tenths % 10 == 0:
        return f"{tenths // 10} ★"
    return f"{tenths / 10:.1f} ★"


def stars_to_tenths(stars: float | int) -> int:
    return int(round(float(stars) * 10))
