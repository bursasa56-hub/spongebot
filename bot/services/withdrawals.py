from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import User, Withdrawal


class WithdrawalError(Exception):
    pass


async def create_withdrawal(
    session: AsyncSession,
    user_id: int,
    gift_id: str,
    gift_name: str,
    gift_stars: int,
    username_to: str,
) -> Withdrawal:
    user = await session.get(User, user_id)
    if user is None:
        raise WithdrawalError("Пользователь не найден.")

    required = gift_stars * 10
    if user.balance_tenths < required:
        raise WithdrawalError("Недостаточно звёзд для этого подарка.")

    pending = await session.execute(
        select(Withdrawal).where(
            Withdrawal.user_id == user_id, Withdrawal.status == "pending"
        )
    )
    if pending.scalar_one_or_none() is not None:
        raise WithdrawalError("У вас уже есть активная заявка на вывод.")

    withdrawal = Withdrawal(
        user_id=user_id,
        gift_id=gift_id,
        gift_name=gift_name,
        gift_stars=gift_stars,
        username_to=username_to.lstrip("@"),
        status="pending",
    )
    session.add(withdrawal)
    await session.commit()
    return withdrawal


async def mark_paid(session: AsyncSession, withdrawal_id: int) -> Withdrawal | None:
    withdrawal = await session.get(Withdrawal, withdrawal_id)
    if withdrawal is None or withdrawal.status == "paid":
        return None

    user = await session.get(User, withdrawal.user_id)
    required = withdrawal.gift_stars * 10
    if user is None or user.balance_tenths < required:
        return None

    user.balance_tenths -= required
    user.total_withdrawn_tenths += required
    withdrawal.status = "paid"
    withdrawal.paid_at = datetime.utcnow()
    await session.commit()
    return withdrawal
