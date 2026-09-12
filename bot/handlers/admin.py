from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ..keyboards.admin import (
    admin_menu_kb,
    sponsors_admin_kb,
    tasks_admin_kb,
)
from ..middlewares.admin_filter import IsAdmin
from ..services.stats import get_stats
from ..services.subscriptions import (
    SponsorError,
    active_sponsors,
    add_bot_sponsor,
    add_channel_sponsor,
    delete_sponsor,
)
from ..services.withdrawals import mark_paid
from ..utils.stars import format_stars

router_admin = Router()


class AdminStates(StatesGroup):
    sponsor_channel_link = State()
    sponsor_bot_link = State()
    task_type = State()
    task_link = State()
    task_title = State()
    task_reward = State()
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


@router_admin.message(Command("admin"), IsAdmin)
async def admin_panel(message: Message) -> None:
    await message.answer("🛠 <b>Админ-панель</b>", reply_markup=admin_menu_kb())


@router_admin.callback_query(F.data == "admin:menu", IsAdmin)
async def admin_back(callback: CallbackQuery) -> None:
    await callback.message.edit_text("🛠 <b>Админ-панель</b>", reply_markup=admin_menu_kb())
    await callback.answer()


@router_admin.callback_query(F.data == "admin:stats", IsAdmin)
async def admin_stats(callback: CallbackQuery, session) -> None:
    stats = await get_stats(session)
    await callback.message.edit_text(
        stats_text(stats), reply_markup=admin_menu_kb()
    )
    await callback.answer()


@router_admin.callback_query(F.data == "admin:sponsors", IsAdmin)
async def admin_sponsors(callback: CallbackQuery, session) -> None:
    sponsors = await active_sponsors(session)
    await callback.message.edit_text(
        "📢 <b>Обязательные спонсоры</b>", reply_markup=sponsors_admin_kb(sponsors)
    )
    await callback.answer()


@router_admin.callback_query(F.data == "admin:sponsor:add_channel", IsAdmin)
async def admin_add_channel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.sponsor_channel_link)
    await callback.message.edit_text(
        "Отправь ссылку на канал (@username, t.me/... или id -100...). "
        "Бот должен быть админом в канале.",
        reply_markup=admin_menu_kb(),
    )
    await callback.answer()


@router_admin.message(AdminStates.sponsor_channel_link, IsAdmin)
async def admin_receive_channel(message: Message, state: FSMContext, session, bot) -> None:
    try:
        sponsor = await add_channel_sponsor(session, bot, message.text or "")
    except SponsorError as exc:
        await message.answer(f"❌ {exc}")
        return
    await state.clear()
    await message.answer(
        f"✅ Канал «{sponsor.title}» добавлен в обязательные.",
        reply_markup=admin_menu_kb(),
    )


@router_admin.callback_query(F.data == "admin:sponsor:add_bot", IsAdmin)
async def admin_add_bot(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.sponsor_bot_link)
    await callback.message.edit_text(
        "Отправь ссылку на бота (@username или t.me/...).",
        reply_markup=admin_menu_kb(),
    )
    await callback.answer()


@router_admin.message(AdminStates.sponsor_bot_link, IsAdmin)
async def admin_receive_bot(message: Message, state: FSMContext, session) -> None:
    try:
        sponsor = await add_bot_sponsor(session, message.text or "")
    except SponsorError as exc:
        await message.answer(f"❌ {exc}")
        return
    await state.clear()
    await message.answer(
        f"✅ Бот {sponsor.title} добавлен в обязательные.",
        reply_markup=admin_menu_kb(),
    )


@router_admin.callback_query(F.data.startswith("admin:sponsor:del:"), IsAdmin)
async def admin_del_sponsor(callback: CallbackQuery, session) -> None:
    sponsor_id = int(callback.data.split(":")[3])
    await delete_sponsor(session, sponsor_id)
    sponsors = await active_sponsors(session)
    await callback.message.edit_text(
        "📢 <b>Обязательные спонсоры</b>", reply_markup=sponsors_admin_kb(sponsors)
    )
    await callback.answer("Удалено")


@router_admin.callback_query(F.data == "admin:tasks", IsAdmin)
async def admin_tasks(callback: CallbackQuery, session) -> None:
    from ..db.models import TaskItem
    from sqlalchemy import select

    res = await session.execute(select(TaskItem).order_by(TaskItem.id))
    tasks = list(res.scalars().all())
    await callback.message.edit_text(
        "📋 <b>Задания</b>", reply_markup=tasks_admin_kb(tasks)
    )
    await callback.answer()


@router_admin.callback_query(F.data.startswith("admin:task:del:"), IsAdmin)
async def admin_del_task(callback: CallbackQuery, session) -> None:
    from sqlalchemy import select

    from ..db.models import TaskItem

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


@router_admin.callback_query(F.data.startswith("wd:paid:"), IsAdmin)
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


TASK_TYPE_LABELS = {"channel": "канал", "bot": "бот"}


@router_admin.callback_query(F.data == "admin:task:add", IsAdmin)
async def admin_task_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.task_type)
    await callback.message.edit_text(
        "Что за задание? Напиши <code>channel</code> (подписка на канал) "
        "или <code>bot</code> (старт в боте).",
        reply_markup=admin_menu_kb(),
    )
    await callback.answer()


@router_admin.message(AdminStates.task_type, IsAdmin)
async def admin_task_type(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip().lower()
    if value not in TASK_TYPE_LABELS:
        await message.answer("Введи channel или bot.")
        return
    await state.update_data(type=value)
    await state.set_state(AdminStates.task_link)
    await message.answer("Отправь ссылку (@username или t.me/...).")


@router_admin.message(AdminStates.task_link, IsAdmin)
async def admin_task_link(message: Message, state: FSMContext) -> None:
    await state.update_data(url=(message.text or "").strip())
    await state.set_state(AdminStates.task_title)
    await message.answer("Отправь название задания.")


@router_admin.message(AdminStates.task_title, IsAdmin)
async def admin_task_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=(message.text or "").strip())
    await state.set_state(AdminStates.task_reward)
    await message.answer("Сколько звёзд за задание? Например 0.5")


@router_admin.message(AdminStates.task_reward, IsAdmin)
async def admin_task_reward(message: Message, state: FSMContext, session) -> None:
    from ..db.models import TaskItem
    from ..utils.stars import stars_to_tenths

    try:
        reward = stars_to_tenths(float((message.text or "").replace(",", ".")))
    except ValueError:
        await message.answer("Введи число, например 0.5")
        return

    data = await state.get_data()
    from ..services.subscriptions import parse_chat_ref

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
        reward_tenths=reward,
    )
    session.add(task)
    await session.commit()
    await state.clear()
    await message.answer(
        f"✅ Задание «{task.title}» добавлено.", reply_markup=admin_menu_kb()
    )


@router_admin.callback_query(F.data == "admin:broadcast", IsAdmin)
async def admin_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.broadcast_text)
    await callback.message.edit_text(
        "Отправь текст рассылки.", reply_markup=admin_menu_kb()
    )
    await callback.answer()


@router_admin.message(AdminStates.broadcast_text, IsAdmin)
async def admin_broadcast_send(message: Message, state: FSMContext, session, bot) -> None:
    from sqlalchemy import select

    from ..db.models import Broadcast, User

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
