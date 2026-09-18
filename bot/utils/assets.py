from __future__ import annotations

from pathlib import Path

from aiogram.types import FSInputFile

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
ASSET_EXTS = (".jpg", ".jpeg", ".png", ".webp")


def asset_path(name: str) -> Path | None:
    base = ASSETS_DIR / name
    for ext in ASSET_EXTS:
        candidate = base.with_suffix(ext)
        if candidate.exists():
            return candidate
    return None


async def send_screen(message, text: str, reply_markup=None, asset: str | None = None) -> None:
    """Send a new screen message: as a photo with caption when the asset exists, else text."""
    if asset:
        path = asset_path(asset)
        if path is not None:
            await message.answer_photo(
                FSInputFile(path), caption=text, reply_markup=reply_markup
            )
            return
    await message.answer(text, reply_markup=reply_markup)


async def replace_screen(callback, text: str, reply_markup=None, asset: str | None = None) -> None:
    try:
        await callback.message.delete()
    except Exception:
        pass
    await send_screen(callback.message, text, reply_markup, asset=asset)
