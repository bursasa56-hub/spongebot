from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ..db.models import User
from ..handlers.captcha import send_captcha
from ..keyboards.user import CHECK_SUBS, MENU_MAIN, main_menu_kb, sponsor_gate_kb
from ..services.referral import credit_referrer, register_user
from ..services.subscriptions import missing_sponsors, needs_referral_captcha
from ..utils.assets import send_screen
from ..utils.stars import format_stars

router_start = Router()

MAIN_MENU_TEXT = (
    "👋 <b>Заработок звёзд</b>\n\n"
    "💰 Приглашай друзей и выполняй задания — получай звёзды.\n"
    "🎁 Звёзды выводятся подарком (от 15 до 100 ★) в течение 24 часов.\n"
    "🎟 Есть промокод? Активируй его кнопкой ниже.\n\n"
    "Выбери раздел:"
)


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
    await send_screen(message, MAIN_MENU_TEXT, main_menu_kb(), asset="menu")


async def _credit_and_notify(session, bot, user_id: int) -> None:
    user = await session.get(User, user_id)
    if user is not None and not user.subscribed:
        user.subscribed = True
        await session.commit()

    referrer = await credit_referrer(session, user_id)
    if referrer is not None:
        try:
            await bot.send_message(
                referrer.id,
                f"🎉 По вашей ссылке зарегистрировался друг! Начислено "
                f"{format_stars(30)}.",
            )
        except Exception:
            pass


@router_start.message(CommandStart())
async def cmd_start(
    message: Message, command: CommandObject, state: FSMContext, session, bot
) -> None:
    user = message.from_user
    ref_id = parse_ref(command.args)
    db_user = await register_user(
        session, user.id, user.username, user.first_name, ref_id
    )

    missing = await missing_sponsors(session, bot, user.id)
    if missing:
        await message.answer(
            "🔒 Для доступа подпишитесь на спонсоров и нажмите «Проверить подписку».",
            reply_markup=sponsor_gate_kb(missing),
        )
        return

    if await needs_referral_captcha(session, db_user):
        await send_captcha(message, state)
        return

    await _credit_and_notify(session, bot, user.id)
    await _show_menu(message, user.id)


@router_start.callback_query(F.data == CHECK_SUBS)
async def check_subs(callback: CallbackQuery, state: FSMContext, session, bot) -> None:
    user = callback.from_user
    missing = await missing_sponsors(session, bot, user.id)
    if missing:
        await callback.answer("❌ Вы подписались не на всех спонсоров.", show_alert=True)
        await callback.message.answer(
            "🔒 Подпишитесь на спонсоров и нажмите «Проверить подписку».",
            reply_markup=sponsor_gate_kb(missing),
        )
        return

    db_user = await session.get(User, user.id)
    if await needs_referral_captcha(session, db_user):
        await send_captcha(callback.message, state)
        await callback.answer()
        return

    await _credit_and_notify(session, bot, user.id)

    await callback.answer("✅ Подписка подтверждена!")
    await send_screen(
        callback.message, MAIN_MENU_TEXT, main_menu_kb(), asset="menu"
    )


@router_start.callback_query(F.data == MENU_MAIN)
async def back_to_main(callback: CallbackQuery, session, bot) -> None:
    missing = await missing_sponsors(session, bot, callback.from_user.id)
    if missing:
        await callback.message.answer(
            "🔒 Подпишитесь на спонсоров и нажмите «Проверить подписку».",
            reply_markup=sponsor_gate_kb(missing),
        )
        await callback.answer()
        return
    await send_screen(
        callback.message, MAIN_MENU_TEXT, main_menu_kb(), asset="menu"
    )
    await callback.answer()
