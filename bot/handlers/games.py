from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ..keyboards.user import (
    MENU_GAMES,
    back_kb,
    bet_kb,
    games_menu_kb,
    rps_kb,
)
from ..services.games import GameError, play_rps
from ..services.referral import get_user
from ..utils.assets import replace_screen
from ..utils.emoji import render
from ..utils.stars import format_stars

router_games = Router()

MOVE_LABELS = {"rock": "🪨 Камень", "scissors": "✂️ Ножницы", "paper": "📄 Бумага"}
OUTCOME_LABELS = {"win": "🎉 Победа!", "lose": "😢 Поражение", "draw": "🤝 Ничья"}


class GameStates(StatesGroup):
    waiting_bet = State()


@router_games.callback_query(F.data == MENU_GAMES)
async def games_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await replace_screen(callback, render("🎮 <b>Игры</b>\n\nВыбери игру:"), games_menu_kb())
    await callback.answer()


@router_games.callback_query(F.data == "game:rps")
async def rps_start(callback: CallbackQuery, state: FSMContext, session) -> None:
    await state.clear()
    user = await get_user(session, callback.from_user.id)
    if user is None:
        await callback.answer("Профиль не найден.", show_alert=True)
        return
    await replace_screen(
        callback,
        render(
            f"🪨✂️📄 <b>Камень-ножницы-бумага</b>\n\n"
            f"Баланс: {format_stars(user.balance_tenths)}\n\nВыбери ставку:"
        ),
        bet_kb(user.balance_tenths),
    )
    await callback.answer()


@router_games.callback_query(F.data.startswith("game:bet:"))
async def rps_bet(callback: CallbackQuery, state: FSMContext, session) -> None:
    value = callback.data.split(":")[2]
    if value == "custom":
        await state.set_state(GameStates.waiting_bet)
        await callback.message.answer(
            render("Отправь сумму ставки в звёздах (минимум 0.5)."), reply_markup=back_kb()
        )
        await callback.answer()
        return
    bet = int(value)
    await state.update_data(bet=bet)
    await state.set_state(None)
    await replace_screen(
        callback, render(f"Ставка: {format_stars(bet)}\n\nВыбери ход:"), rps_kb()
    )
    await callback.answer()


@router_games.message(GameStates.waiting_bet)
async def rps_custom_bet(message: Message, state: FSMContext, session) -> None:
    from ..utils.stars import stars_to_tenths

    try:
        bet = stars_to_tenths(float((message.text or "").replace(",", ".")))
    except ValueError:
        await message.answer(render("Введи число, например 0.5"), reply_markup=back_kb())
        return
    user = await get_user(session, message.from_user.id)
    if user is None or bet < 5 or bet > user.balance_tenths:
        await message.answer(
            render("❌ Ставка должна быть от 0.5 ★ и не больше твоего баланса."),
            reply_markup=back_kb(),
        )
        return
    await state.update_data(bet=bet)
    await state.set_state(None)
    await message.answer(
        render(f"Ставка: {format_stars(bet)}\n\nВыбери ход:"), reply_markup=rps_kb()
    )


@router_games.callback_query(F.data.startswith("game:move:"))
async def rps_move(callback: CallbackQuery, state: FSMContext, session) -> None:
    move = callback.data.split(":")[2]
    data = await state.get_data()
    bet = data.get("bet")
    if not bet:
        await callback.answer("Сначала выбери ставку.", show_alert=True)
        return
    try:
        result = await play_rps(session, callback.from_user.id, bet, move)
    except GameError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    user = await get_user(session, callback.from_user.id)
    text = render(
        f"{OUTCOME_LABELS[result['outcome']]}\n\n"
        f"Ты: {MOVE_LABELS[result['user_move']]}\n"
        f"Бот: {MOVE_LABELS[result['bot_move']]}\n"
        f"Ставка: {format_stars(result['bet'])}\n\n"
        f"💰 Баланс: {format_stars(user.balance_tenths)}"
    )
    await replace_screen(callback, text, rps_kb())
    await callback.answer()
