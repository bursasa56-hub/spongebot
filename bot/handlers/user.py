from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from ..keyboards.user import (
    MENU_EARN,
    MENU_INSTRUCTION,
    MENU_PROFILE,
    back_kb,
    earn_kb,
    instruction_kb,
)
from ..services.referral import count_referrals, get_user
from ..utils.stars import format_stars

router_user = Router()

INSTRUCTION_TEXT = (
    "📖 <b>Как заработать звёзды</b>\n\n"
    "1. Приглашай друзей по своей реферальной ссылке — за каждого друга, "
    "который подпишется на всех спонсоров, ты получаешь 3 ★.\n"
    "2. Выполняй задания в разделе «Задания» — по 0.5 ★ за каждое.\n"
    "3. Оставляй ссылку в описании профиля и делись с друзьями.\n\n"
    "Звёзды можно вывести подарком (от 15 до 100 ★) в разделе «Вывод звёзд».\n\n"
    "Если что-то не работает — напиши в поддержку."
)


def profile_text(user, bot_username: str, invited: int) -> str:
    ref_link = f"https://t.me/{bot_username}?start=ref_{user.id}"
    return (
        "👤 <b>Твой профиль</b>\n\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"👥 Приглашено друзей: {invited}\n"
        f"💰 Баланс: {format_stars(user.balance_tenths)}\n"
        f"📈 Всего заработано: {format_stars(user.total_earned_tenths)}\n"
        f"💸 Всего выведено: {format_stars(user.total_withdrawn_tenths)}\n\n"
        f"🔗 Твоя ссылка:\n<code>{ref_link}</code>"
    )


@router_user.callback_query(F.data == MENU_PROFILE)
async def show_profile(callback: CallbackQuery, session, bot) -> None:
    user = await get_user(session, callback.from_user.id)
    invited = await count_referrals(session, user.id)
    me = await bot.get_me()
    await callback.message.edit_text(
        profile_text(user, me.username, invited), reply_markup=back_kb()
    )
    await callback.answer()


@router_user.callback_query(F.data == MENU_INSTRUCTION)
async def show_instruction(callback: CallbackQuery, support_url: str) -> None:
    await callback.message.edit_text(
        INSTRUCTION_TEXT, reply_markup=instruction_kb(support_url)
    )
    await callback.answer()


@router_user.callback_query(F.data == MENU_EARN)
async def show_earn(callback: CallbackQuery, bot) -> None:
    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{callback.from_user.id}"
    text = (
        "💰 <b>Как заработать звёзды</b>\n\n"
        "• Отправляй реферальную ссылку друзьям и родственникам.\n"
        "• Оставь ссылку в описании своего профиля.\n"
        "• Публикуй её в чатах и каналах.\n\n"
        "За каждого друга, который подпишется на всех спонсоров — 3 ★.\n\n"
        f"🔗 Твоя ссылка:\n<code>{ref_link}</code>"
    )
    await callback.message.edit_text(text, reply_markup=earn_kb(ref_link))
    await callback.answer()
