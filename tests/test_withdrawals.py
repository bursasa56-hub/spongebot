import pytest

from bot.db.models import User
from bot.services.withdrawals import (
    WithdrawalError,
    create_withdrawal,
    mark_paid,
)


async def _rich_user(session, uid=1, tenths=200):
    session.add(User(id=uid, username="u", first_name="U", balance_tenths=tenths))
    await session.commit()


@pytest.mark.asyncio
async def test_cannot_withdraw_more_than_balance(session):
    await _rich_user(session, tenths=100)
    with pytest.raises(WithdrawalError):
        await create_withdrawal(session, 1, "bear", "Медвежонок", 15, "@friend")


@pytest.mark.asyncio
async def test_create_and_mark_paid(session):
    await _rich_user(session, tenths=200)
    w = await create_withdrawal(session, 1, "bear", "Медвежонок", 15, "@friend")
    assert w.status == "pending"
    assert w.username_to == "friend"

    paid = await mark_paid(session, w.id)
    assert paid is not None
    assert paid.status == "paid"
    user = await session.get(User, 1)
    assert user.balance_tenths == 50
    assert user.total_withdrawn_tenths == 150


@pytest.mark.asyncio
async def test_mark_paid_idempotent(session):
    await _rich_user(session, tenths=200)
    w = await create_withdrawal(session, 1, "bear", "Медвежонок", 15, "@friend")
    await mark_paid(session, w.id)
    assert await mark_paid(session, w.id) is None
    user = await session.get(User, 1)
    assert user.balance_tenths == 50


@pytest.mark.asyncio
async def test_second_pending_withdrawal_rejected(session):
    await _rich_user(session, tenths=400)
    await create_withdrawal(session, 1, "bear", "Медвежонок", 15, "@friend")
    with pytest.raises(WithdrawalError):
        await create_withdrawal(session, 1, "bear", "Медвежонок", 15, "@friend2")


@pytest.mark.asyncio
async def test_new_withdrawal_allowed_after_paid(session):
    await _rich_user(session, tenths=400)
    w = await create_withdrawal(session, 1, "bear", "Медвежонок", 15, "@friend")
    await mark_paid(session, w.id)
    again = await create_withdrawal(session, 1, "bear", "Медвежонок", 15, "@friend")
    assert again.status == "pending"
