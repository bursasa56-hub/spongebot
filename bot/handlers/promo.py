from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ..keyboards.user import MENU_PROMO, cancel_kb
from ..services.promos import PromoError, redeem_promo
from ..utils.assets import replace_screen
from ..utils.emoji import render

router_promo = Router()


class PromoStates(StatesGroup):
    waiting_code = State()


@router_promo.callback_query(F.data == MENU_PROMO)
async def ask_promo(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PromoStates.waiting_code)
    await replace_screen(
        callback,
        render("🎟 Отправь промокод сообщением."),
        cancel_kb(),
        asset="promo",
    )
    await callback.answer()


@router_promo.message(PromoStates.waiting_code)
async def apply_promo(message: Message, state: FSMContext, session) -> None:
    await state.clear()
    try:
        promo = await redeem_promo(session, message.from_user.id, message.text or "")
    except PromoError as exc:
        await message.answer(render(f"❌ {exc}"), reply_markup=cancel_kb())
        return
    await message.answer(
        render(f"✅ Промокод активирован! Начислено {promo.stars} ★."),
        reply_markup=cancel_kb(),
    )
