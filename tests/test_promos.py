import pytest

from bot.db.models import User
from bot.services.promos import (
    PromoError,
    create_promo,
    delete_promo,
    list_promos,
    redeem_promo,
)


async def _add_user(session, user_id=1):
    session.add(User(id=user_id, username=f"u{user_id}", first_name="U"))
    await session.commit()


@pytest.mark.asyncio
async def test_create_promo_and_duplicate_rejected(session):
    promo = await create_promo(session, "SALE", 5, 0)
    assert promo.code == "SALE"
    assert promo.stars == 5
    assert promo.max_uses == 0
    assert [p.id for p in await list_promos(session)] == [promo.id]

    with pytest.raises(PromoError):
        await create_promo(session, "SALE", 5, 0)


@pytest.mark.asyncio
async def test_create_promo_validation(session):
    with pytest.raises(PromoError):
        await create_promo(session, "   ", 5, 0)
    with pytest.raises(PromoError):
        await create_promo(session, "ZERO", 0, 0)
    with pytest.raises(PromoError):
        await create_promo(session, "NEG", 5, -1)


@pytest.mark.asyncio
async def test_redeem_credits_stars_times_ten_once(session):
    await _add_user(session, 1)
    await create_promo(session, "GIFT", 3, 0)

    promo = await redeem_promo(session, 1, "GIFT")
    assert promo.stars == 3

    user = await session.get(User, 1)
    assert user.balance_tenths == 30
    assert user.total_earned_tenths == 30

    with pytest.raises(PromoError):
        await redeem_promo(session, 1, "GIFT")
    user = await session.get(User, 1)
    assert user.balance_tenths == 30


@pytest.mark.asyncio
async def test_redeem_unknown_code_rejected(session):
    await _add_user(session, 1)
    with pytest.raises(PromoError):
        await redeem_promo(session, 1, "NOPE")


@pytest.mark.asyncio
async def test_redeem_limit_exhausted_for_second_user(session):
    await _add_user(session, 1)
    await _add_user(session, 2)
    await create_promo(session, "ONE", 2, 1)

    await redeem_promo(session, 1, "ONE")
    with pytest.raises(PromoError):
        await redeem_promo(session, 2, "ONE")

    user2 = await session.get(User, 2)
    assert user2.balance_tenths == 0


@pytest.mark.asyncio
async def test_delete_promo(session):
    promo = await create_promo(session, "TMP", 1, 0)
    assert await delete_promo(session, promo.id) is True
    assert await list_promos(session) == []
    assert await delete_promo(session, promo.id) is False


@pytest.mark.asyncio
async def test_redeem_exhausted_promo_auto_deleted(session):
    from bot.db.models import PromoCode

    await _add_user(session, 1)
    promo = await create_promo(session, "AUTO", 1, 1)

    returned = await redeem_promo(session, 1, "AUTO")

    assert returned.stars == 1
    assert await session.get(PromoCode, promo.id) is None
    assert await list_promos(session) == []


@pytest.mark.asyncio
async def test_unlimited_promo_not_deleted(session):
    await _add_user(session, 1)
    await create_promo(session, "UNLIM", 1, 0)

    await redeem_promo(session, 1, "UNLIM")

    assert [p.code for p in await list_promos(session)] == ["UNLIM"]
