from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from ..keyboards.user import main_menu_kb
from ..services.referral import credit_referrer
from ..utils.captcha import build_captcha
from ..utils.stars import format_stars

router_captcha = Router()


async def send_captcha(message, state: FSMContext) -> None:
    target, options = build_captcha()
    await state.update_data(captcha_target=target)
    rows = [
        [InlineKeyboardButton(text=emoji, callback_data=f"captcha:{emoji}")]
        for emoji in options
    ]
    await message.answer(
        f"🤖 Подтверди, что ты человек.\nНажми на: <b>{target}</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router_captcha.callback_query(F.data.startswith("captcha:"))
async def captcha_answer(callback: CallbackQuery, state: FSMContext, session, bot) -> None:
    answer = callback.data.split(":", 1)[1]
    data = await state.get_data()
    target = data.get("captcha_target")
    if not target or answer != target:
        await callback.answer("❌ Неверно, попробуй снова.", show_alert=True)
        await send_captcha(callback.message, state)
        return
    await state.clear()
    referrer = await credit_referrer(session, callback.from_user.id)
    if referrer is not None:
        try:
            await bot.send_message(
                referrer.id,
                f"🎉 По вашей ссылке зарегистрировался друг! Начислено {format_stars(30)}.",
            )
        except Exception:
            pass
    await callback.answer("✅ Проверка пройдена!")
    await callback.message.answer(
        "✅ Проверка пройдена! Теперь ты можешь пользоваться ботом.",
        reply_markup=main_menu_kb(),
    )
