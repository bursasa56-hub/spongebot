from __future__ import annotations

from aiogram import Router
from aiogram.types import ChatJoinRequest
from sqlalchemy import select

from ..db.models import Sponsor, TaskItem
from ..services.subscriptions import mark_sponsor_done
from ..services.tasks import complete_task

router_join = Router()


@router_join.chat_join_request()
async def on_join_request(update: ChatJoinRequest, session) -> None:
    res = await session.execute(
        select(Sponsor).where(
            Sponsor.chat_id == str(update.chat.id),
            Sponsor.active.is_(True),
        )
    )
    sponsor = res.scalar_one_or_none()
    if sponsor is not None:
        await mark_sponsor_done(session, update.from_user.id, sponsor.id)

    tasks = await session.execute(
        select(TaskItem).where(
            TaskItem.chat_id == str(update.chat.id),
            TaskItem.active.is_(True),
            TaskItem.type == "channel",
            TaskItem.subtype == "private_request",
        )
    )
    for task in tasks.scalars().all():
        await complete_task(session, update.from_user.id, task.id)
