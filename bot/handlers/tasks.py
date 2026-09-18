from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from ..keyboards.user import MENU_TASKS, back_kb, task_kb
from ..services.tasks import available_tasks, complete_task, self_verifiable
from ..utils.assets import replace_screen
from ..utils.emoji import render
from ..utils.stars import format_stars

router_tasks = Router()


async def next_task(session, user_id: int, exclude_id: int | None = None):
    tasks = await available_tasks(session, user_id)
    for task in tasks:
        if task.id != exclude_id:
            return task
    return None


def task_body(task) -> str:
    return (
        f"<b>{task.title}</b>\n\n"
        f"Награда: {format_stars(task.reward_tenths)}"
    )


def task_text(task) -> str:
    return render("📋 <b>Задание</b>\n\n" + task_body(task))


@router_tasks.callback_query(F.data == MENU_TASKS)
async def show_tasks(callback: CallbackQuery, session) -> None:
    tasks = await available_tasks(session, callback.from_user.id)
    if not tasks:
        await replace_screen(
            callback,
            render("📋 <b>Задания</b>\n\nПока нет доступных заданий. Заходи позже!"),
            back_kb(),
        )
        await callback.answer()
        return
    task = tasks[0]
    await replace_screen(
        callback,
        render(f"📋 <b>Задания</b> (доступно: {len(tasks)})\n\n" + task_body(task)),
        task_kb(task),
    )
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
        await replace_screen(
            callback,
            render("📋 <b>Задания</b>\n\nПока нет доступных заданий. Заходи позже!"),
            back_kb(),
        )
    else:
        await replace_screen(callback, task_text(nxt), task_kb(nxt))


@router_tasks.callback_query(F.data.startswith("task:skip:"))
async def skip_task(callback: CallbackQuery, session) -> None:
    current_id = int(callback.data.split(":")[2])
    nxt = await next_task(session, callback.from_user.id, exclude_id=current_id)
    if nxt is None:
        await callback.answer("Больше заданий нет.", show_alert=True)
        await replace_screen(
            callback,
            render("📋 <b>Задания</b>\n\nПока нет доступных заданий. Заходи позже!"),
            back_kb(),
        )
        return
    await replace_screen(callback, task_text(nxt), task_kb(nxt))
    await callback.answer()
