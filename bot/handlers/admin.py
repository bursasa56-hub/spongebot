from __future__ import annotations

import html
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from ..db.models import Broadcast, Sponsor, TaskItem, User, Withdrawal
from ..keyboards.admin import (
    admin_menu_kb,
    partner_choice_kb,
    partners_admin_kb,
    settings_admin_kb,
    sponsors_admin_kb,
    tasks_admin_kb,
)
from ..middlewares.admin_filter import IsAdmin
from ..services.partners import (
    create_partner,
    delete_partner,
    get_partner,
    list_partners,
)
from ..services.settings import API_BASE_URL_KEY, get_setting, set_setting
from ..services.snippets import build_snippet
from ..services.stats import get_stats
from ..services.subscriptions import (
    SponsorError,
    add_bot_sponsor,
    add_channel_sponsor,
    all_sponsors,
    delete_sponsor,
    parse_chat_ref,
    sponsor_status,
)
from ..services.withdrawals import mark_paid
from ..utils.stars import format_stars, stars_to_tenths

router_admin = Router()


class AdminStates(StatesGroup):
    sponsor_link = State()
    sponsor_hours = State()
    sponsor_quota = State()
    sponsor_partner = State()
    task_type = State()
    task_link = State()
    task_title = State()
    task_reward = State()
    task_partner = State()
    partner_name = State()
    settings_api_url = State()
    broadcast_text = State()


def stats_text(stats) -> str:
    return (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: {stats.total_users}\n"
        f"🆕 Новых за сегодня: {stats.new_today}\n"
        f"📅 Новых за 7 дней: {stats.new_week}\n"
        f"🗓 Новых за месяц: {stats.new_month}\n"
        f"🤝 Приглашено друзей: {stats.referrals}\n"
        f"💰 Начислено: {format_stars(stats.earned_tenths)}\n"
        f"💸 Выплачено: {format_stars(stats.withdrawn_tenths)}\n"
        f"⏳ Активных заявок: {stats.pending_withdrawals}\n"
        f"✅ Выполнено заданий: {stats.tasks_done}"
    )


async def _send_snippet(message, session, partner_id, *, task_id=None, sponsor_id=None) -> None:
    api_base = await get_setting(session, API_BASE_URL_KEY)
    partner = await get_partner(session, partner_id) if partner_id else None
    api_key = partner.api_key if partner else None
    snippet = build_snippet(api_base, api_key, task_id=task_id, sponsor_id=sponsor_id)
    await message.answer(
        "🔑 <b>Код для партнёрского бота:</b>\n<pre><code>"
        + html.escape(snippet)
        + "</code></pre>"
    )


@router_admin.message(Command("admin"), IsAdmin())
async def admin_panel(message: Message) -> None:
    await message.answer("🛠 <b>Админ-панель</b>", reply_markup=admin_menu_kb())


@router_admin.callback_query(F.data == "admin:menu", IsAdmin())
async def admin_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("🛠 <b>Админ-панель</b>", reply_markup=admin_menu_kb())
    await callback.answer()


@router_admin.callback_query(F.data == "admin:stats", IsAdmin())
async def admin_stats(callback: CallbackQuery, session) -> None:
    stats = await get_stats(session)
    await callback.message.edit_text(
        stats_text(stats), reply_markup=admin_menu_kb()
    )
    await callback.answer()


@router_admin.callback_query(F.data == "admin:partners", IsAdmin())
async def admin_partners(callback: CallbackQuery, session) -> None:
    partners = await list_partners(session)
    await callback.message.edit_text(
        "🤝 <b>Партнёры</b>", reply_markup=partners_admin_kb(partners)
    )
    await callback.answer()


@router_admin.callback_query(F.data == "admin:partner:add", IsAdmin())
async def admin_partner_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.partner_name)
    await callback.message.edit_text(
        "Отправь название партнёра.", reply_markup=admin_menu_kb()
    )
    await callback.answer()


@router_admin.message(AdminStates.partner_name, IsAdmin())
async def admin_partner_name(message: Message, state: FSMContext, session) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Введи название.")
        return
    partner = await create_partner(session, name)
    await state.clear()
    await message.answer(
        f"✅ Партнёр «{html.escape(partner.name)}» добавлен.\n"
        f"🔑 API-ключ: <code>{html.escape(partner.api_key)}</code>",
        reply_markup=admin_menu_kb(),
    )


@router_admin.callback_query(F.data.startswith("admin:partner:key:"), IsAdmin())
async def admin_partner_key(callback: CallbackQuery, session) -> None:
    partner_id = int(callback.data.split(":")[3])
    partner = await get_partner(session, partner_id)
    if partner is None:
        await callback.answer("Партнёр не найден.", show_alert=True)
        return
    await callback.message.answer(
        f"🔑 <b>Ключ партнёра «{html.escape(partner.name)}»:</b>\n"
        f"<code>{html.escape(partner.api_key)}</code>",
        reply_markup=admin_menu_kb(),
    )
    await callback.answer()


@router_admin.callback_query(F.data.startswith("admin:partner:del:"), IsAdmin())
async def admin_partner_del(callback: CallbackQuery, session) -> None:
    partner_id = int(callback.data.split(":")[3])
    await delete_partner(session, partner_id)
    partners = await list_partners(session)
    await callback.message.edit_text(
        "🤝 <b>Партнёры</b>", reply_markup=partners_admin_kb(partners)
    )
    await callback.answer("Удалено")


@router_admin.callback_query(F.data == "admin:settings", IsAdmin())
async def admin_settings(callback: CallbackQuery, session) -> None:
    value = await get_setting(session, API_BASE_URL_KEY)
    shown = html.escape(value) if value else "не задан"
    await callback.message.edit_text(
        f"⚙️ <b>Настройки</b>\n\nАдрес API: <code>{shown}</code>",
        reply_markup=settings_admin_kb(),
    )
    await callback.answer()


@router_admin.callback_query(F.data == "admin:settings:api_url", IsAdmin())
async def admin_settings_api_url(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.settings_api_url)
    await callback.message.edit_text(
        "Отправь базовый адрес API, например https://example.com",
        reply_markup=admin_menu_kb(),
    )
    await callback.answer()


@router_admin.message(AdminStates.settings_api_url, IsAdmin())
async def admin_settings_api_url_save(message: Message, state: FSMContext, session) -> None:
    value = (message.text or "").strip()
    if not value:
        await message.answer("Введи адрес.")
        return
    await set_setting(session, API_BASE_URL_KEY, value)
    await state.clear()
    await message.answer(
        f"✅ Адрес API сохранён: <code>{html.escape(value)}</code>",
        reply_markup=admin_menu_kb(),
    )


@router_admin.callback_query(F.data == "admin:sponsors", IsAdmin())
async def admin_sponsors(callback: CallbackQuery, session) -> None:
    sponsors = await all_sponsors(session)
    statuses = {s.id: await sponsor_status(session, s) for s in sponsors}
    await callback.message.edit_text(
        "📢 <b>Обязательные спонсоры</b>",
        reply_markup=sponsors_admin_kb(sponsors, statuses),
    )
    await callback.answer()


@router_admin.callback_query(F.data == "admin:sponsor:add_channel", IsAdmin())
async def admin_add_channel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.sponsor_link)
    await state.update_data(type="channel")
    await callback.message.edit_text(
        "Отправь ссылку на канал (@username, t.me/... или id -100...). "
        "Бот должен быть админом в канале.",
        reply_markup=admin_menu_kb(),
    )
    await callback.answer()


@router_admin.callback_query(F.data == "admin:sponsor:add_bot", IsAdmin())
async def admin_add_bot(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.sponsor_link)
    await state.update_data(type="bot")
    await callback.message.edit_text(
        "Отправь ссылку на бота (@username или t.me/...).",
        reply_markup=admin_menu_kb(),
    )
    await callback.answer()


@router_admin.message(AdminStates.sponsor_link, IsAdmin())
async def admin_sponsor_link(message: Message, state: FSMContext) -> None:
    await state.update_data(link=(message.text or "").strip())
    await state.set_state(AdminStates.sponsor_hours)
    await message.answer("Срок действия в часах (0 = бессрочно).")


@router_admin.message(AdminStates.sponsor_hours, IsAdmin())
async def admin_sponsor_hours(message: Message, state: FSMContext) -> None:
    try:
        hours = int((message.text or "").strip())
        if hours < 0:
            raise ValueError
    except ValueError:
        await message.answer("Введи целое число ≥ 0.")
        return
    await state.update_data(hours=hours)
    await state.set_state(AdminStates.sponsor_quota)
    await message.answer("Лимит прохождений (0 = без лимита).")


@router_admin.message(AdminStates.sponsor_quota, IsAdmin())
async def admin_sponsor_quota(message: Message, state: FSMContext, session, bot) -> None:
    try:
        quota = int((message.text or "").strip())
        if quota < 0:
            raise ValueError
    except ValueError:
        await message.answer("Введи целое число ≥ 0.")
        return
    await state.update_data(quota=quota)
    data = await state.get_data()
    if data.get("type") == "bot":
        partners = await list_partners(session)
        await state.set_state(AdminStates.sponsor_partner)
        await message.answer(
            "Выбери партнёра:",
            reply_markup=partner_choice_kb(partners, "admin:sponsor:partner"),
        )
    else:
        await _finish_sponsor(bot, message, state, session, None)


@router_admin.callback_query(F.data.startswith("admin:sponsor:partner:"), IsAdmin())
async def admin_sponsor_partner(
    callback: CallbackQuery, state: FSMContext, session, bot
) -> None:
    partner_id = int(callback.data.split(":")[3]) or None
    await _finish_sponsor(bot, callback.message, state, session, partner_id)
    await callback.answer()


async def _finish_sponsor(bot, message, state: FSMContext, session, partner_id) -> None:
    data = await state.get_data()
    hours = data.get("hours", 0)
    quota = data.get("quota", 0)
    link = data.get("link", "")
    sponsor_type = data.get("type", "channel")
    expires_at = datetime.utcnow() + timedelta(hours=hours) if hours else None
    try:
        if sponsor_type == "channel":
            sponsor = await add_channel_sponsor(
                session,
                bot,
                link,
                expires_at=expires_at,
                max_completions=quota,
                partner_id=partner_id,
            )
        else:
            sponsor = await add_bot_sponsor(
                session,
                link,
                expires_at=expires_at,
                max_completions=quota,
                partner_id=partner_id,
            )
    except SponsorError as exc:
        await state.clear()
        await message.answer(f"❌ {exc}", reply_markup=admin_menu_kb())
        return
    await state.clear()
    await message.answer(
        f"✅ Спонсор «{html.escape(sponsor.title)}» добавлен в обязательные.",
        reply_markup=admin_menu_kb(),
    )
    if sponsor.type == "bot":
        await _send_snippet(message, session, sponsor.partner_id, sponsor_id=sponsor.id)


@router_admin.callback_query(F.data.startswith("admin:sponsor:code:"), IsAdmin())
async def admin_sponsor_code(callback: CallbackQuery, session) -> None:
    sponsor_id = int(callback.data.split(":")[3])
    sponsor = await session.get(Sponsor, sponsor_id)
    if sponsor is None:
        await callback.answer("Спонсор не найден.", show_alert=True)
        return
    await _send_snippet(callback.message, session, sponsor.partner_id, sponsor_id=sponsor.id)
    await callback.answer()


@router_admin.callback_query(F.data.startswith("admin:sponsor:del:"), IsAdmin())
async def admin_del_sponsor(callback: CallbackQuery, session) -> None:
    sponsor_id = int(callback.data.split(":")[3])
    await delete_sponsor(session, sponsor_id)
    sponsors = await all_sponsors(session)
    statuses = {s.id: await sponsor_status(session, s) for s in sponsors}
    await callback.message.edit_text(
        "📢 <b>Обязательные спонсоры</b>",
        reply_markup=sponsors_admin_kb(sponsors, statuses),
    )
    await callback.answer("Удалено")


@router_admin.callback_query(F.data == "admin:tasks", IsAdmin())
async def admin_tasks(callback: CallbackQuery, session) -> None:
    res = await session.execute(select(TaskItem).order_by(TaskItem.id))
    tasks = list(res.scalars().all())
    await callback.message.edit_text(
        "📋 <b>Задания</b>", reply_markup=tasks_admin_kb(tasks)
    )
    await callback.answer()


@router_admin.callback_query(F.data.startswith("admin:task:del:"), IsAdmin())
async def admin_del_task(callback: CallbackQuery, session) -> None:
    task_id = int(callback.data.split(":")[3])
    task = await session.get(TaskItem, task_id)
    if task is not None:
        task.active = False
        await session.commit()
    res = await session.execute(select(TaskItem).where(TaskItem.active.is_(True)))
    tasks = list(res.scalars().all())
    await callback.message.edit_text(
        "📋 <b>Задания</b>", reply_markup=tasks_admin_kb(tasks)
    )
    await callback.answer("Удалено")


@router_admin.callback_query(F.data.startswith("wd:paid:"), IsAdmin())
async def admin_mark_paid(callback: CallbackQuery, session, bot) -> None:
    withdrawal_id = int(callback.data.split(":")[2])
    withdrawal = await mark_paid(session, withdrawal_id)
    if withdrawal is None:
        await callback.answer("Уже выплачено или недостаточно баланса.", show_alert=True)
        return
    try:
        await callback.message.edit_text(
            callback.message.html_text + "\n\n✅ <b>Выплачено</b>"
        )
    except Exception:
        pass
    try:
        await bot.send_message(
            withdrawal.user_id,
            "🎁 Админ отправил вам подарок! Проверьте подарки в Telegram.",
        )
    except Exception:
        pass
    await callback.answer("Отмечено как выплачено")


@router_admin.callback_query(F.data == "admin:withdrawals", IsAdmin())
async def admin_withdrawals(callback: CallbackQuery, session) -> None:
    res = await session.execute(
        select(Withdrawal)
        .where(Withdrawal.status == "pending")
        .order_by(Withdrawal.id)
    )
    items = list(res.scalars().all())
    if not items:
        text = "💸 Нет активных заявок."
    else:
        lines = ["💸 <b>Активные заявки на вывод:</b>\n"]
        for w in items:
            lines.append(
                f"#{w.id} — {w.gift_name} ({w.gift_stars}★) → @{w.username_to} "
                f"(id <code>{w.user_id}</code>)"
            )
        text = "\n".join(lines)

    rows = []
    for w in items:
        if w.admin_chat_id is not None and w.admin_msg_id is not None:
            internal = str(w.admin_chat_id).removeprefix("-100")
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"#{w.id}",
                        url=f"https://t.me/c/{internal}/{w.admin_msg_id}",
                    )
                ]
            )
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:menu")])
    await callback.message.edit_text(
        text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await callback.answer()


TASK_TYPE_LABELS = {"channel": "канал", "bot": "бот"}


@router_admin.callback_query(F.data == "admin:task:add", IsAdmin())
async def admin_task_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.task_type)
    await callback.message.edit_text(
        "Что за задание? Напиши <code>channel</code> (подписка на канал) "
        "или <code>bot</code> (старт в боте).",
        reply_markup=admin_menu_kb(),
    )
    await callback.answer()


@router_admin.message(AdminStates.task_type, IsAdmin())
async def admin_task_type(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip().lower()
    if value not in TASK_TYPE_LABELS:
        await message.answer("Введи channel или bot.")
        return
    await state.update_data(type=value)
    await state.set_state(AdminStates.task_link)
    await message.answer("Отправь ссылку (@username или t.me/...).")


@router_admin.message(AdminStates.task_link, IsAdmin())
async def admin_task_link(message: Message, state: FSMContext) -> None:
    await state.update_data(url=(message.text or "").strip())
    await state.set_state(AdminStates.task_title)
    await message.answer("Отправь название задания.")


@router_admin.message(AdminStates.task_title, IsAdmin())
async def admin_task_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=(message.text or "").strip())
    await state.set_state(AdminStates.task_reward)
    await message.answer("Сколько звёзд за задание? Например 0.5")


@router_admin.message(AdminStates.task_reward, IsAdmin())
async def admin_task_reward(message: Message, state: FSMContext, session) -> None:
    try:
        reward = stars_to_tenths(float((message.text or "").replace(",", ".")))
    except ValueError:
        await message.answer("Введи число, например 0.5")
        return

    await state.update_data(reward=reward)
    data = await state.get_data()

    if data["type"] == "bot":
        partners = await list_partners(session)
        await state.set_state(AdminStates.task_partner)
        await message.answer(
            "Выбери партнёра:",
            reply_markup=partner_choice_kb(partners, "admin:task:partner"),
        )
    else:
        await _finish_task(message, state, session, None)


@router_admin.callback_query(F.data.startswith("admin:task:partner:"), IsAdmin())
async def admin_task_partner(callback: CallbackQuery, state: FSMContext, session) -> None:
    partner_id = int(callback.data.split(":")[3]) or None
    await _finish_task(callback.message, state, session, partner_id)
    await callback.answer()


async def _finish_task(message, state: FSMContext, session, partner_id) -> None:
    data = await state.get_data()

    try:
        chat_ref = parse_chat_ref(data["url"])
    except SponsorError as exc:
        await state.clear()
        await message.answer(f"❌ {exc}", reply_markup=admin_menu_kb())
        return

    task = TaskItem(
        type=data["type"],
        title=data["title"],
        url=data["url"],
        chat_id=chat_ref if data["type"] == "channel" else None,
        reward_tenths=data["reward"],
        partner_id=partner_id,
    )
    session.add(task)
    await session.commit()
    await state.clear()
    await message.answer(
        f"✅ Задание «{html.escape(task.title)}» добавлено.",
        reply_markup=admin_menu_kb(),
    )
    if task.type == "bot":
        await _send_snippet(message, session, task.partner_id, task_id=task.id)


@router_admin.callback_query(F.data.startswith("admin:task:code:"), IsAdmin())
async def admin_task_code(callback: CallbackQuery, session) -> None:
    task_id = int(callback.data.split(":")[3])
    task = await session.get(TaskItem, task_id)
    if task is None:
        await callback.answer("Задание не найдено.", show_alert=True)
        return
    await _send_snippet(callback.message, session, task.partner_id, task_id=task.id)
    await callback.answer()


@router_admin.callback_query(F.data == "admin:broadcast", IsAdmin())
async def admin_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.broadcast_text)
    await callback.message.edit_text(
        "Отправь текст рассылки.", reply_markup=admin_menu_kb()
    )
    await callback.answer()


@router_admin.message(AdminStates.broadcast_text, IsAdmin())
async def admin_broadcast_send(message: Message, state: FSMContext, session, bot) -> None:
    await state.clear()
    res = await session.execute(select(User.id).where(User.is_blocked.is_(False)))
    user_ids = list(res.scalars().all())
    sent = failed = 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, message.text or "")
            sent += 1
        except Exception:
            failed += 1
    session.add(Broadcast(text=message.text or "", sent_count=sent, failed_count=failed))
    await session.commit()
    await message.answer(
        f"✅ Рассылка завершена. Доставлено: {sent}, ошибок: {failed}.",
        reply_markup=admin_menu_kb(),
    )
