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
            [_btn("🤝 Партнёры", "admin:partners"), _btn("⚙️ Настройки", "admin:settings")],
        ]
    )


def partners_admin_kb(partners) -> InlineKeyboardMarkup:
    rows = [[_btn("➕ Добавить партнёра", "admin:partner:add")]]
    for p in partners:
        rows.append([_btn(f"🗑 {p.name}", f"admin:partner:del:{p.id}")])
    rows.append([_btn("⬅️ Назад", "admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def partner_choice_kb(partners, prefix: str) -> InlineKeyboardMarkup:
    rows = [[_btn(p.name, f"{prefix}:{p.id}")] for p in partners]
    rows.append([_btn("Без партнёра", f"{prefix}:0")])
    rows.append([_btn("⬅️ Назад", "admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def settings_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("✏️ Изменить адрес API", "admin:settings:api_url")],
            [_btn("⬅️ Назад", "admin:menu")],
        ]
    )


def sponsors_admin_kb(sponsors, statuses: dict[int, str]) -> InlineKeyboardMarkup:
    rows = [[_btn("➕ Добавить канал", "admin:sponsor:add_channel")],
            [_btn("➕ Добавить бота", "admin:sponsor:add_bot")]]
    for s in sponsors:
        row = [
            _btn(
                f"🗑 #{s.id} {s.title} — {statuses.get(s.id, '')}",
                f"admin:sponsor:del:{s.id}",
            )
        ]
        if s.type == "bot":
            row.append(_btn("🔑 Код", f"admin:sponsor:code:{s.id}"))
        rows.append(row)
    rows.append([_btn("⬅️ Назад", "admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def tasks_admin_kb(tasks) -> InlineKeyboardMarkup:
    rows = [[_btn("➕ Добавить задание", "admin:task:add")]]
    for t in tasks:
        row = [_btn(f"🗑 #{t.id} {t.title}", f"admin:task:del:{t.id}")]
        if t.type == "bot":
            row.append(_btn("🔑 Код", f"admin:task:code:{t.id}"))
        rows.append(row)
    rows.append([_btn("⬅️ Назад", "admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def withdraw_admin_kb(withdrawal_id: int, username_to: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 Профиль заказчика", url=f"https://t.me/{username_to}")],
            [_btn("✅ Выплачено", f"wd:paid:{withdrawal_id}")],
        ]
    )
