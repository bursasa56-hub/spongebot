from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def _btn(text: str, callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data)


def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("📢 Спонсоры", "admin:sponsors"), _btn("📋 Задания", "admin:tasks")],
            [_btn("✉️ Рассылка", "admin:broadcast"), _btn("📊 Статистика", "admin:stats")],
            [_btn("💸 Заявки на вывод", "admin:withdrawals")],
            [_btn("⚙️ Настройки", "admin:settings")],
            [_btn("🎟 Промокоды", "admin:promos")],
            [_btn("🧹 Обнулить звёзды", "admin:reset")],
        ]
    )


def back_to_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[_btn("⬅️ Назад", "admin:menu")]])


def settings_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn("✏️ Изменить адрес API", "admin:settings:api_url")],
            [_btn("⬅️ Назад", "admin:menu")],
        ]
    )


def sponsors_admin_kb(sponsors, statuses: dict[int, str]) -> InlineKeyboardMarkup:
    rows = [[_btn("➕ Добавить спонсора", "admin:sponsor:add")]]
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


def sponsor_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_btn("📢 Канал/чат", "admin:sponsor:type:channel"), _btn("🤖 Бот", "admin:sponsor:type:bot")],
        [_btn("⬅️ Назад", "admin:menu")],
    ])


def sponsor_limit_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_btn("🔢 На количество", "admin:sponsor:limit:quota")],
        [_btn("⏳ На время", "admin:sponsor:limit:time")],
        [_btn("♾ Навсегда", "admin:sponsor:limit:forever")],
        [_btn("⬅️ Назад", "admin:menu")],
    ])


def sponsor_channel_subtype_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_btn("📢 Публичный канал/чат", "admin:sponsor:subtype:public_channel")],
        [_btn("🔒 Частный чат/канал", "admin:sponsor:subtype:private_request")],
        [_btn("⬅️ Назад", "admin:menu")],
    ])


def promos_admin_kb(promos) -> InlineKeyboardMarkup:
    rows = [[_btn("➕ Создать промокод", "admin:promo:add")]]
    for p in promos:
        limit = p.max_uses if p.max_uses else "∞"
        rows.append([
            _btn(f"🗑 {p.code} — {p.stars}★ ({p.used_count}/{limit})", f"admin:promo:del:{p.id}")
        ])
    rows.append([_btn("⬅️ Назад", "admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def task_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_btn("📢 Канал", "admin:task:type:channel"), _btn("🤖 Бот", "admin:task:type:bot")],
        [_btn("⬅️ Назад", "admin:menu")],
    ])


def task_channel_subtype_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_btn("📢 Публичный канал", "admin:task:subtype:public_channel")],
        [_btn("💬 Чат (группа)", "admin:task:subtype:chat")],
        [_btn("🔒 Частный канал (заявка)", "admin:task:subtype:private_request")],
        [_btn("⬅️ Назад", "admin:menu")],
    ])


def task_duration_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_btn("♾ Бессрочно", "admin:task:duration:0")],
        [_btn("⏳ На время", "admin:task:duration:1")],
        [_btn("⬅️ Назад", "admin:menu")],
    ])


def task_quota_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_btn("♾ Без лимита", "admin:task:quota:0")],
        [_btn("🔢 На количество", "admin:task:quota:1")],
        [_btn("⬅️ Назад", "admin:menu")],
    ])


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
