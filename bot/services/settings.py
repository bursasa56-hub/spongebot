from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Setting

API_BASE_URL_KEY = "api_base_url"


async def get_setting(session: AsyncSession, key: str, default: str | None = None) -> str | None:
    setting = await session.get(Setting, key)
    return setting.value if setting is not None else default


async def set_setting(session: AsyncSession, key: str, value: str) -> None:
    setting = await session.get(Setting, key)
    if setting is None:
        session.add(Setting(key=key, value=value))
    else:
        setting.value = value
    await session.commit()
