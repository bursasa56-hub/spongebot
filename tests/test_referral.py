import pytest

from bot.db.models import User
from bot.services.referral import (
    REFERRAL_REWARD_TENTHS,
    count_referrals,
    credit_referrer,
    register_user,
)


@pytest.mark.asyncio
async def test_register_new_user_with_referrer(session):
    await register_user(session, 1, "owner", "Owner")
    friend = await register_user(session, 2, "friend", "Friend", ref_id=1)
    assert friend.referred_by == 1
    assert friend.referral_credited is False


@pytest.mark.asyncio
async def test_self_referral_ignored(session):
    user = await register_user(session, 1, "a", "A", ref_id=1)
    assert user.referred_by is None


@pytest.mark.asyncio
async def test_credit_referrer_once(session):
    await register_user(session, 1, "owner", "Owner")
    await register_user(session, 2, "friend", "Friend", ref_id=1)

    referrer = await credit_referrer(session, 2)
    assert referrer is not None
    assert referrer.balance_tenths == REFERRAL_REWARD_TENTHS
    assert referrer.total_earned_tenths == REFERRAL_REWARD_TENTHS

    again = await credit_referrer(session, 2)
    assert again is None
    owner = await session.get(User, 1)
    assert owner.balance_tenths == REFERRAL_REWARD_TENTHS


@pytest.mark.asyncio
async def test_repeat_start_does_not_change_referrer(session):
    await register_user(session, 1, "owner", "Owner")
    await register_user(session, 2, "friend", "Friend", ref_id=1)
    user = await register_user(session, 2, "friend", "Friend", ref_id=99)
    assert user.referred_by == 1


@pytest.mark.asyncio
async def test_count_referrals(session):
    await register_user(session, 1, "owner", "Owner")
    await register_user(session, 2, "f1", "F1", ref_id=1)
    await register_user(session, 3, "f2", "F2", ref_id=1)
    await register_user(session, 4, "other", "O", ref_id=2)
    assert await count_referrals(session, 1) == 2
