from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from ..keyboards.user import MENU_DAILY, back_kb
from ..services.daily import DailyError, claim_daily
from ..utils.assets import replace_screen
from ..utils.stars import format_stars

router_daily = Router()


@router_daily.callback_query(F.data == MENU_DAILY)
async def claim_daily_reward(callback: CallbackQuery, session, bot) -> None:
    try:
        chat = await bot.get_chat(callback.from_user.id)
    except Exception:
        chat = None
    bio = getattr(chat, "bio", None) if chat is not None else None
    try:
        reward = await claim_daily(session, callback.from_user.id, bio)
    except DailyError as exc:
        await replace_screen(callback, f"❌ {exc}", back_kb())
        await callback.answer()
        return
    await replace_screen(
        callback,
        f"🎁 Ежедневная награда получена: +{format_stars(reward)}",
        back_kb(),
    )
    await callback.answer()
