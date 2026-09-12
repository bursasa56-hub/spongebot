from datetime import datetime, timedelta

import pytest

from bot.db.models import User, Withdrawal
from bot.services.stats import get_stats


@pytest.mark.asyncio
async def test_stats_counts(session):
    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    user2_created = max(now - timedelta(days=3), month_start + timedelta(seconds=1))

    session.add_all(
        [
            User(id=1, created_at=now, balance_tenths=30, total_earned_tenths=30),
            User(
                id=2,
                created_at=user2_created,
                referred_by=1,
                referral_credited=True,
            ),
            User(id=3, created_at=now - timedelta(days=40)),
        ]
    )
    session.add(
        Withdrawal(
            user_id=1,
            gift_id="bear",
            gift_name="Медвежонок",
            gift_stars=15,
            username_to="x",
            status="pending",
        )
    )
    await session.commit()

    stats = await get_stats(session)
    assert stats.total_users == 3
    assert stats.new_today == 1 + int(user2_created >= day_ago)
    assert stats.new_week == 2
    assert stats.new_month == 2
    assert stats.referrals == 1
    assert stats.earned_tenths == 30
    assert stats.pending_withdrawals == 1
