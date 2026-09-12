from __future__ import annotations

from aiogram import Router
from aiogram.types import ChatJoinRequest
from sqlalchemy import select

from ..db.models import Sponsor
from ..services.subscriptions import mark_sponsor_done

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
    if sponsor is None:
        return
    await mark_sponsor_done(session, update.from_user.id, sponsor.id)
