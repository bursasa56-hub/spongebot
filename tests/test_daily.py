import pytest

from bot.db.models import User
from bot.services.daily import (
    DAILY_REWARD_TENTHS,
    DailyError,
    bio_has_ref,
    claim_daily,
)
from bot.services.referral import register_user


def test_bio_has_ref():
    assert bio_has_ref("...ref_5...", 5) is True
    assert bio_has_ref("no", 5) is False
    assert bio_has_ref(None, 5) is False


@pytest.mark.asyncio
async def test_claim_daily_grants_once_per_day(session):
    await register_user(session, 5, "u", "U")

    reward = await claim_daily(session, 5, "my ref_5 link")
    assert reward == DAILY_REWARD_TENTHS

    user = await session.get(User, 5)
    assert user.balance_tenths == DAILY_REWARD_TENTHS
    assert user.total_earned_tenths == DAILY_REWARD_TENTHS
    assert user.last_daily_at is not None

    with pytest.raises(DailyError):
        await claim_daily(session, 5, "my ref_5 link")


@pytest.mark.asyncio
async def test_claim_daily_requires_ref_in_bio(session):
    await register_user(session, 5, "u", "U")

    with pytest.raises(DailyError):
        await claim_daily(session, 5, "nothing here")

    user = await session.get(User, 5)
    assert user.balance_tenths == 0
