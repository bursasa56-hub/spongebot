from __future__ import annotations

from urllib.parse import quote

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..utils.gifts import FIXED_GIFTS
from ..utils.stars import format_stars

MENU_MAIN = "menu:main"
MENU_PROFILE = "menu:profile"
MENU_INSTRUCTION = "menu:instruction"
MENU_TASKS = "menu:tasks"
MENU_GAMES = "menu:games"
MENU_WITHDRAW = "menu:withdraw"
MENU_EARN = "menu:earn"
MENU_PROMO = "menu:promo"
MENU_DAILY = "menu:daily"
CHECK_SUBS = "check_subs"


def _btn(text: str, callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data)


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("💰 Заработать звёзды", MENU_EARN)],
            [_btn("🎁 Ежедневная награда", MENU_DAILY)],
            [_btn("👤 Профиль", MENU_PROFILE)],
            [_btn("📋 Задания", MENU_TASKS)],
            [_btn("🎮 Игры", MENU_GAMES)],
            [_btn("💸 Вывод звёзд", MENU_WITHDRAW)],
            [_btn("🎟 Промокод", MENU_PROMO)],
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
    rows = []
    if getattr(task, "url", None):
        label = "▶️ Перейти в бота" if task.type == "bot" else "➡️ Подписаться"
        rows.append([InlineKeyboardButton(text=label, url=task.url)])
    rows.append([_btn("✅ Проверить", f"task:check:{task.id}")])
    rows.append([_btn("⏭ Пропустить", f"task:skip:{task.id}")])
    rows.append([_btn("⬅️ Назад", MENU_MAIN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def games_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_btn("🪨✂️📄 Камень-ножницы-бумага", "game:rps")],
        [_btn("⬅️ Назад", MENU_MAIN)],
    ])


def bet_kb(balance_tenths: int) -> InlineKeyboardMarkup:
    rows = []
    for tenths in (5, 10, 20, 50, 100):
        if tenths <= balance_tenths:
            rows.append([_btn(f"⭐ Ставка {format_stars(tenths)}", f"game:bet:{tenths}")])
    rows.append([_btn("✏️ Своя сумма", "game:bet:custom")])
    rows.append([_btn("⬅️ Назад", MENU_MAIN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def rps_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_btn("🪨 Камень", "game:move:rock"), _btn("✂️ Ножницы", "game:move:scissors")],
        [_btn("📄 Бумага", "game:move:paper")],
        [_btn("⬅️ Назад", MENU_MAIN)],
    ])


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


def gifts_kb() -> InlineKeyboardMarkup:
    rows = []
    row = []
    for gift in FIXED_GIFTS:
        row.append(_btn(f"{gift.emoji} {gift.stars} ★", f"wd:gift:{gift.id}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([_btn("🎁 Подарить другу", "wd:friend")])
    rows.append([_btn("⬅️ Назад", MENU_MAIN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[_btn("⬅️ Назад", MENU_MAIN)]])
