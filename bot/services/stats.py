from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import User, UserTask, Withdrawal


@dataclass
class Stats:
    total_users: int
    new_today: int
    new_week: int
    new_month: int
    referrals: int
    earned_tenths: int
    withdrawn_tenths: int
    pending_withdrawals: int
    tasks_done: int


async def _count(session: AsyncSession, query) -> int:
    return (await session.execute(query)).scalar_one()


async def get_stats(session: AsyncSession) -> Stats:
    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    return Stats(
        total_users=await _count(session, select(func.count()).select_from(User)),
        new_today=await _count(
            session, select(func.count()).select_from(User).where(User.created_at >= day_ago)
        ),
        new_week=await _count(
            session, select(func.count()).select_from(User).where(User.created_at >= week_ago)
        ),
        new_month=await _count(
            session,
            select(func.count()).select_from(User).where(User.created_at >= month_start),
        ),
        referrals=await _count(
            session,
            select(func.count())
            .select_from(User)
            .where(User.referral_credited.is_(True)),
        ),
        earned_tenths=await _count(
            session, select(func.coalesce(func.sum(User.total_earned_tenths), 0))
        ),
        withdrawn_tenths=await _count(
            session, select(func.coalesce(func.sum(User.total_withdrawn_tenths), 0))
        ),
        pending_withdrawals=await _count(
            session,
            select(func.count())
            .select_from(Withdrawal)
            .where(Withdrawal.status == "pending"),
        ),
        tasks_done=await _count(
            session, select(func.count()).select_from(UserTask)
        ),
    )
