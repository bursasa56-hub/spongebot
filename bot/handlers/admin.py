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
