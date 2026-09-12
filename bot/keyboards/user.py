from __future__ import annotations

from urllib.parse import quote

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..utils.gifts import FIXED_GIFTS
from ..utils.stars import format_stars

MENU_MAIN = "menu:main"
MENU_PROFILE = "menu:profile"
MENU_INSTRUCTION = "menu:instruction"
MENU_TASKS = "menu:tasks"
MENU_WITHDRAW = "menu:withdraw"
MENU_EARN = "menu:earn"
CHECK_SUBS = "check_subs"


def _btn(text: str, callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data)


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("💰 Заработать звёзды", MENU_EARN)],
            [_btn("👤 Профиль", MENU_PROFILE)],
            [_btn("📋 Задания", MENU_TASKS)],
            [_btn("💸 Вывод звёзд", MENU_WITHDRAW)],
            [_btn("📖 Инструкция", MENU_INSTRUCTION)],
        ]
    )


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[_btn("⬅️ Назад", MENU_MAIN)]])


def sponsor_gate_kb(sponsors) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"➡️ {s.title}", url=s.url)] for s in sponsors
    ]
    rows.append([_btn("✅ Проверить подписку", CHECK_SUBS)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def instruction_kb(support_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🆘 Поддержка", url=support_url)],
            [_btn("⬅️ Назад", MENU_MAIN)],
        ]
    )


def task_kb(task) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("✅ Проверить", f"task:check:{task.id}")],
            [_btn("⏭ Пропустить", f"task:skip:{task.id}")],
            [_btn("⬅️ Назад", MENU_MAIN)],
        ]
    )


def earn_kb(ref_link: str) -> InlineKeyboardMarkup:
    share = (
        f"https://t.me/share/url?url={quote(ref_link, safe='')}"
        f"&text={quote('Заработай звёзды!')}"
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📤 Поделиться", url=share)],
            [_btn("⬅️ Назад", MENU_MAIN)],
        ]
    )


def gifts_kb(balance_tenths: int) -> InlineKeyboardMarkup:
    rows = []
    for gift in FIXED_GIFTS:
        if gift.stars * 10 <= balance_tenths:
            rows.append(
                [
                    _btn(
                        f"{gift.emoji} {gift.name} — {format_stars(gift.stars * 10)}",
                        f"wd:gift:{gift.id}",
                    )
                ]
            )
    rows.append([_btn("⬅️ Назад", MENU_MAIN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[_btn("⬅️ Назад", MENU_MAIN)]])
