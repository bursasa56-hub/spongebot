from __future__ import annotations

import html
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ..keyboards.admin import withdraw_admin_kb
from ..keyboards.user import MENU_WITHDRAW, cancel_kb, gifts_kb
from ..services.referral import count_referrals, get_user
from ..services.withdrawals import WithdrawalError, create_withdrawal
from ..utils.assets import send_screen
from ..utils.gifts import GIFTS_BY_ID
from ..utils.stars import format_stars

router_withdraw = Router()

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{5,32}$")

MIN_INVITED = 5


class WithdrawStates(StatesGroup):
    waiting_username = State()


def normalize_username(text: str) -> str | None:
    text = text.strip()
    if "t.me/" in text:
        text = text.split("t.me/", 1)[1].split("/")[0]
    text = text.lstrip("@")
    if USERNAME_RE.match(text):
        return text
    return None


def withdraw_text(balance_tenths: int, invited: int) -> str:
    return (
        f"💵 <b>Баланс:</b> {format_stars(balance_tenths)}\n\n"
        "❗️ <b>Для вывода требуется:</b>\n"
        "— Минимум <b>5</b> приглашённых друзей, активировавших бота\n"
        "— Быть подписанным на спонсоров\n\n"
        "✅ Вывод обрабатывает администратор.\n\n"
        "Выбери подарок, который хочешь получить или отправить другу:"
    )


@router_withdraw.callback_query(F.data == MENU_WITHDRAW)
async def show_gifts(callback: CallbackQuery, session) -> None:
    user = await get_user(session, callback.from_user.id)
    if user is None:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    invited = await count_referrals(session, user.id)
    if invited < MIN_INVITED:
        await send_screen(
            callback.message,
            withdraw_text(user.balance_tenths, invited)
            + "\n\n❌ Пока нельзя: пригласи минимум 5 друзей.",
            cancel_kb(),
            asset="withdraw",
        )
        await callback.answer()
        return
    await send_screen(
        callback.message,
        withdraw_text(user.balance_tenths, invited),
        gifts_kb(),
        asset="withdraw",
    )
    await callback.answer()


@router_withdraw.callback_query(F.data == "wd:friend")
async def gift_to_friend(callback: CallbackQuery, state: FSMContext, session) -> None:
    user = await get_user(session, callback.from_user.id)
    if user is None:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    invited = await count_referrals(session, user.id)
    if invited < MIN_INVITED:
        await callback.answer("Нужно минимум 5 друзей.", show_alert=True)
        return
    await state.update_data(to_friend=True)
    await send_screen(
        callback.message,
        withdraw_text(user.balance_tenths, invited)
        + "\n\n🎁 Выбери подарок для друга:",
        gifts_kb(),
        asset="withdraw",
    )
    await callback.answer()


@router_withdraw.callback_query(F.data.startswith("wd:gift:"))
async def choose_gift(
    callback: CallbackQuery, state: FSMContext, session
) -> None:
    gift_id = callback.data.split(":")[2]
    gift = GIFTS_BY_ID.get(gift_id)
    if gift is None:
        await callback.answer("Подарок не найден.", show_alert=True)
        return
    user = await get_user(session, callback.from_user.id)
    invited = await count_referrals(session, user.id) if user is not None else 0
    if invited < MIN_INVITED:
        await callback.answer("Нужно минимум 5 друзей.", show_alert=True)
        return
    to_friend = (await state.get_data()).get("to_friend", False)
    await state.update_data(gift_id=gift.id)
    await state.set_state(WithdrawStates.waiting_username)
    prompt = (
        "Отправь <b>@username</b> друга, которому подарить звёзды:"
        if to_friend
        else "Отправь <b>@username</b>, куда вывести звёзды:"
    )
    await callback.message.answer(
        f"🎁 Выбран подарок: {gift.emoji} {gift.name} — {format_stars(gift.stars * 10)}\n\n"
        f"{prompt}",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router_withdraw.message(WithdrawStates.waiting_username)
async def receive_username(
    message: Message, state: FSMContext, session, config
) -> None:
    username = normalize_username(message.text or "")
    if username is None:
        await message.answer(
            "❌ Некорректный username. Пример: <code>@username</code>",
            reply_markup=cancel_kb(),
        )
        return

    data = await state.get_data()
    to_friend = data.get("to_friend", False)
    gift = GIFTS_BY_ID.get(data.get("gift_id", ""))
    if gift is None:
        await state.clear()
        await message.answer("Подарок не найден. Начни заново.", reply_markup=cancel_kb())
        return

    user = await get_user(session, message.from_user.id)
    invited = await count_referrals(session, user.id) if user is not None else 0
    if invited < MIN_INVITED:
        await state.clear()
        await message.answer(
            "❌ Пока нельзя: пригласи минимум 5 друзей.",
            reply_markup=cancel_kb(),
        )
        return

    try:
        withdrawal = await create_withdrawal(
            session,
            message.from_user.id,
            gift.id,
            gift.name,
            gift.stars,
            username,
        )
    except WithdrawalError as exc:
        await state.clear()
        await message.answer(f"❌ {exc}", reply_markup=cancel_kb())
        return

    await state.clear()

    header = "🎁 Подарок другу" if to_friend else "💸 Вывод звёзд"
    admin_text = (
        f"{header}\n\n"
        f"🎁 Подарок: {gift.emoji} {gift.name} — {format_stars(gift.stars * 10)}\n"
        f"👤 Заказчик: {html.escape(message.from_user.full_name)} "
        f"(@{message.from_user.username or '—'}, <code>{message.from_user.id}</code>)\n"
        f"📥 Вывести на: @{username}\n"
        f"🕒 Заявка #{withdrawal.id}"
    )
    try:
        admin_msg = await message.bot.send_message(
            config.admin_chat_id,
            admin_text,
            reply_markup=withdraw_admin_kb(withdrawal.id, username),
        )
    except Exception:
        await session.delete(withdrawal)
        await session.commit()
        await message.answer(
            "⚠️ Не удалось отправить заявку. Попробуй позже.",
            reply_markup=cancel_kb(),
        )
        return
    withdrawal.admin_chat_id = admin_msg.chat.id
    withdrawal.admin_msg_id = admin_msg.message_id
    await session.commit()

    await message.answer(
        "✅ Заявка отправлена! После проверки админ отправит подарок.",
        reply_markup=cancel_kb(),
    )
