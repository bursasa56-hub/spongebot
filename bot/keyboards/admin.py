from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def _btn(text: str, callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data)


def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("📢 Спонсоры", "admin:sponsors")],
            [_btn("📋 Задания", "admin:tasks")],
            [_btn("✉️ Рассылка", "admin:broadcast")],
            [_btn("📊 Статистика", "admin:stats")],
            [_btn("💸 Заявки на вывод", "admin:withdrawals")],
        ]
    )


def sponsors_admin_kb(sponsors) -> InlineKeyboardMarkup:
    rows = [[_btn("➕ Добавить канал", "admin:sponsor:add_channel")],
            [_btn("➕ Добавить бота", "admin:sponsor:add_bot")]]
    for s in sponsors:
        rows.append([_btn(f"🗑 {s.title}", f"admin:sponsor:del:{s.id}")])
    rows.append([_btn("⬅️ Назад", "admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def tasks_admin_kb(tasks) -> InlineKeyboardMarkup:
    rows = [[_btn("➕ Добавить задание", "admin:task:add")]]
    for t in tasks:
        rows.append([_btn(f"🗑 {t.title}", f"admin:task:del:{t.id}")])
    rows.append([_btn("⬅️ Назад", "admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def withdraw_admin_kb(withdrawal_id: int, username_to: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 Профиль заказчика", url=f"https://t.me/{username_to}")],
            [_btn("✅ Выплачено", f"wd:paid:{withdrawal_id}")],
        ]
    )
