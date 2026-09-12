from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import User

REFERRAL_REWARD_TENTHS = 30


async def get_user(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def register_user(
    session: AsyncSession,
    user_id: int,
    username: str | None,
    first_name: str | None,
    ref_id: int | None = None,
) -> User:
    user = await session.get(User, user_id)
    if user is None:
        user = User(id=user_id, username=username, first_name=first_name)
        if ref_id is not None and ref_id != user_id:
            user.referred_by = ref_id
        session.add(user)
    else:
        if username != user.username:
            user.username = username
        if first_name != user.first_name:
            user.first_name = first_name
    await session.commit()
    return user


async def credit_referrer(session: AsyncSession, friend_id: int) -> User | None:
    friend = await session.get(User, friend_id)
    if friend is None or friend.referred_by is None or friend.referral_credited:
        return None

    referrer = await session.get(User, friend.referred_by)
    friend.referral_credited = True
    if referrer is None:
        await session.commit()
        return None

    referrer.balance_tenths += REFERRAL_REWARD_TENTHS
    referrer.total_earned_tenths += REFERRAL_REWARD_TENTHS
    await session.commit()
    return referrer


async def count_referrals(session: AsyncSession, user_id: int) -> int:
    from sqlalchemy import func, select

    return (
        await session.execute(
            select(func.count()).select_from(User).where(User.referred_by == user_id)
        )
    ).scalar_one()
