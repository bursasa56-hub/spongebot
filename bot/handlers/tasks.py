from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from ..keyboards.user import MENU_TASKS, main_menu_kb, task_kb
from ..services.tasks import available_tasks, complete_task, self_verifiable
from ..utils.stars import format_stars

router_tasks = Router()


async def next_task(session, user_id: int, exclude_id: int | None = None):
    tasks = await available_tasks(session, user_id)
    for task in tasks:
        if task.id != exclude_id:
            return task
    return None


def task_text(task) -> str:
    return (
        f"📋 <b>Задание</b>\n\n{task.title}\n\n"
        f"Награда: {format_stars(task.reward_tenths)}"
    )


@router_tasks.callback_query(F.data == MENU_TASKS)
async def show_tasks(callback: CallbackQuery, session) -> None:
    task = await next_task(session, callback.from_user.id)
    if task is None:
        await callback.message.answer(
            "📋 Пока нет доступных заданий. Заходи позже!", reply_markup=main_menu_kb()
        )
        await callback.answer()
        return
    await callback.message.answer(task_text(task), reply_markup=task_kb(task))
    await callback.answer()


@router_tasks.callback_query(F.data.startswith("task:check:"))
async def check_task(callback: CallbackQuery, session, bot) -> None:
    from ..db.models import TaskItem

    task_id = int(callback.data.split(":")[2])
    task = await session.get(TaskItem, task_id)
    if task is None or not task.active:
        await callback.answer("Задание недоступно.", show_alert=True)
        return

    if task.type == "bot":
        await callback.answer(
            "Сначала нажмите /start у партнёрского бота — задание засчитается автоматически.",
            show_alert=True,
        )
        return

    if not await self_verifiable(bot, task, callback.from_user.id):
        await callback.answer("❌ Вы ещё не подписались.", show_alert=True)
        return

    done = await complete_task(session, callback.from_user.id, task_id)
    if done is None:
        await callback.answer("Уже выполнено.", show_alert=True)
    else:
        await callback.answer(f"✅ Начислено {format_stars(done.reward_tenths)}")

    nxt = await next_task(session, callback.from_user.id)
    if nxt is None:
        await callback.message.answer(
            "📋 Задания закончились! Заходи позже.", reply_markup=main_menu_kb()
        )
    else:
        await callback.message.answer(task_text(nxt), reply_markup=task_kb(nxt))


@router_tasks.callback_query(F.data.startswith("task:skip:"))
async def skip_task(callback: CallbackQuery, session) -> None:
    current_id = int(callback.data.split(":")[2])
    nxt = await next_task(session, callback.from_user.id, exclude_id=current_id)
    if nxt is None:
        await callback.answer("Больше заданий нет.", show_alert=True)
        await callback.message.answer(
            "📋 Пока нет доступных заданий. Заходи позже!", reply_markup=main_menu_kb()
        )
        return
    await callback.message.answer(task_text(nxt), reply_markup=task_kb(nxt))
    await callback.answer()
