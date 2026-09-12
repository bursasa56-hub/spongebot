from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message

from ..keyboards.user import CHECK_SUBS, MENU_MAIN, main_menu_kb, sponsor_gate_kb
from ..services.referral import credit_referrer, register_user
from ..services.subscriptions import missing_sponsors
from ..utils.stars import format_stars

router_start = Router()

WELCOME = "👋 Добро пожаловать в бота для заработка звёзд!"


def parse_ref(payload: str | None) -> int | None:
    if not payload:
        return None
    token = payload.strip().split()[-1]
    if token.startswith("ref_"):
        token = token[4:]
    if token.isdigit():
        return int(token)
    return None


async def _show_menu(message: Message, user_id: int, edit: bool = False) -> None:
    text = (
        f"{WELCOME}\n\n"
        "Выбери раздел в меню ниже."
    )
    if edit:
        await message.edit_text(text, reply_markup=main_menu_kb())
    else:
        await message.answer(text, reply_markup=main_menu_kb())


@router_start.message(CommandStart())
async def cmd_start(
    message: Message, command: CommandObject, session, bot
) -> None:
    user = message.from_user
    ref_id = parse_ref(command.args)
    await register_user(session, user.id, user.username, user.first_name, ref_id)

    missing = await missing_sponsors(session, bot, user.id)
    if missing:
        await message.answer(
            "🔒 Для доступа подпишитесь на спонсоров и нажмите «Проверить подписку».",
            reply_markup=sponsor_gate_kb(missing),
        )
        return

    await _show_menu(message, user.id)


@router_start.callback_query(F.data == CHECK_SUBS)
async def check_subs(callback: CallbackQuery, session, bot) -> None:
    user = callback.from_user
    missing = await missing_sponsors(session, bot, user.id)
    if missing:
        await callback.answer("❌ Вы подписались не на всех спонсоров.", show_alert=True)
        await callback.message.edit_text(
            "🔒 Подпишитесь на спонсоров и нажмите «Проверить подписку».",
            reply_markup=sponsor_gate_kb(missing),
        )
        return

    referrer = await credit_referrer(session, user.id)
    if referrer is not None:
        try:
            await bot.send_message(
                referrer.id,
                f"🎉 По вашей ссылке зарегистрировался друг! Начислено "
                f"{format_stars(30)}.",
            )
        except Exception:
            pass

    await callback.answer("✅ Подписка подтверждена!")
    await callback.message.edit_text(
        f"{WELCOME}\n\nВыбери раздел в меню ниже.", reply_markup=main_menu_kb()
    )


@router_start.callback_query(F.data == MENU_MAIN)
async def back_to_main(callback: CallbackQuery, session, bot) -> None:
    missing = await missing_sponsors(session, bot, callback.from_user.id)
    if missing:
        await callback.message.edit_text(
            "🔒 Подпишитесь на спонсоров и нажмите «Проверить подписку».",
            reply_markup=sponsor_gate_kb(missing),
        )
        await callback.answer()
        return
    await callback.message.edit_text(
        f"{WELCOME}\n\nВыбери раздел в меню ниже.", reply_markup=main_menu_kb()
    )
    await callback.answer()
