import pytest

from bot.services.settings import get_setting, set_setting


@pytest.mark.asyncio
async def test_set_then_get(session):
    await set_setting(session, "api_base_url", "https://example.com")
    assert await get_setting(session, "api_base_url") == "https://example.com"


@pytest.mark.asyncio
async def test_get_default(session):
    assert await get_setting(session, "missing", "fallback") == "fallback"
    assert await get_setting(session, "missing") is None
