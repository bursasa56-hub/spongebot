import pytest

from bot.services.partners import (
    create_partner,
    delete_partner,
    get_partner,
    list_partners,
    verify_key,
)


@pytest.mark.asyncio
async def test_create_partner_generates_unique_key(session):
    first = await create_partner(session, "First")
    second = await create_partner(session, "Second")
    assert first.api_key
    assert second.api_key
    assert first.api_key != second.api_key


@pytest.mark.asyncio
async def test_verify_key(session):
    partner = await create_partner(session, "First")
    found = await verify_key(session, partner.api_key)
    assert found is not None
    assert found.id == partner.id


@pytest.mark.asyncio
async def test_verify_key_unknown_or_empty(session):
    assert await verify_key(session, "nope") is None
    assert await verify_key(session, None) is None


@pytest.mark.asyncio
async def test_verify_key_inactive(session):
    partner = await create_partner(session, "First")
    partner.active = False
    await session.commit()
    assert await verify_key(session, partner.api_key) is None


@pytest.mark.asyncio
async def test_list_and_get_and_delete(session):
    first = await create_partner(session, "First")
    await create_partner(session, "Second")
    assert [p.id for p in await list_partners(session)] == [first.id, first.id + 1]
    assert (await get_partner(session, first.id)).name == "First"
    assert await delete_partner(session, first.id) is True
    assert await delete_partner(session, first.id) is False
    assert await get_partner(session, first.id) is None
