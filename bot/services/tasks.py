from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import TaskItem, User, UserTask
from .subscriptions import is_member


async def count_task_completions(session: AsyncSession, task_id: int) -> int:
    from sqlalchemy import func

    return (
        await session.execute(
            select(func.count()).select_from(UserTask).where(UserTask.task_id == task_id)
        )
    ).scalar_one()


async def available_tasks(session: AsyncSession, user_id: int) -> list[TaskItem]:
    from datetime import datetime

    now = datetime.utcnow()
    done = select(UserTask.task_id).where(UserTask.user_id == user_id)
    res = await session.execute(
        select(TaskItem)
        .where(TaskItem.active.is_(True), TaskItem.id.not_in(done))
        .order_by(TaskItem.id)
    )
    result = []
    for task in res.scalars().all():
        if task.expires_at is not None and task.expires_at <= now:
            continue
        if task.max_completions and (
            await count_task_completions(session, task.id) >= task.max_completions
        ):
            continue
        result.append(task)
    return result


async def complete_task(
    session: AsyncSession, user_id: int, task_id: int
) -> TaskItem | None:
    task = await session.get(TaskItem, task_id)
    if task is None or not task.active:
        return None

    already = await session.execute(
        select(UserTask).where(
            UserTask.user_id == user_id, UserTask.task_id == task_id
        )
    )
    if already.scalar_one_or_none() is not None:
        return None

    user = await session.get(User, user_id)
    if user is None:
        return None

    session.add(UserTask(user_id=user_id, task_id=task_id))
    user.balance_tenths += task.reward_tenths
    user.total_earned_tenths += task.reward_tenths
    await session.commit()
    return task


async def is_channel_member(bot, chat_id: str, user_id: int) -> bool:
    return await is_member(bot, chat_id, user_id)


async def self_verifiable(bot, task, user_id: int) -> bool:
    if task.type != "channel":
        return False
    return await is_channel_member(bot, task.chat_id or task.url, user_id)
