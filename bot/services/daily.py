from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import User

DAILY_REWARD_TENTHS = 10
DAILY_INTERVAL = timedelta(hours=24)


class DailyError(Exception):
    pass


def bio_has_ref(bio: str | None, user_id: int) -> bool:
    return f"ref_{user_id}" in (bio or "")


async def claim_daily(session: AsyncSession, user_id: int, bio: str | None) -> int:
    user = await session.get(User, user_id)
    if user is None:
        raise DailyError("Профиль не найден.")
    if not bio_has_ref(bio, user_id):
        raise DailyError(
            "Добавь свою реферальную ссылку в описание профиля и попробуй снова."
        )
    now = datetime.utcnow()
    if user.last_daily_at is not None and now - user.last_daily_at < DAILY_INTERVAL:
        raise DailyError("Награда уже получена. Приходи позже.")
    user.balance_tenths += DAILY_REWARD_TENTHS
    user.total_earned_tenths += DAILY_REWARD_TENTHS
    user.last_daily_at = now
    await session.commit()
    return DAILY_REWARD_TENTHS
