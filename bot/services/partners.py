from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Partner


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


async def create_partner(session: AsyncSession, name: str) -> Partner:
    partner = Partner(name=name, api_key=generate_api_key())
    session.add(partner)
    await session.commit()
    return partner


async def list_partners(session: AsyncSession) -> list[Partner]:
    res = await session.execute(select(Partner).order_by(Partner.id))
    return list(res.scalars().all())


async def get_partner(session: AsyncSession, partner_id: int) -> Partner | None:
    return await session.get(Partner, partner_id)


async def delete_partner(session: AsyncSession, partner_id: int) -> bool:
    partner = await session.get(Partner, partner_id)
    if partner is None:
        return False
    await session.delete(partner)
    await session.commit()
    return True


async def verify_key(session: AsyncSession, api_key: str | None) -> Partner | None:
    if not api_key:
        return None
    res = await session.execute(
        select(Partner).where(Partner.api_key == api_key, Partner.active.is_(True))
    )
    return res.scalar_one_or_none()
