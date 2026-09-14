from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import PromoCode, PromoUse, User


class PromoError(Exception):
    pass


async def create_promo(session: AsyncSession, code: str, stars: int, max_uses: int) -> PromoCode:
    code = code.strip()
    if not code:
        raise PromoError("Код не может быть пустым.")
    if stars <= 0:
        raise PromoError("Количество звёзд должно быть больше нуля.")
    if max_uses < 0:
        raise PromoError("Лимит не может быть отрицательным.")
    existing = await session.execute(select(PromoCode).where(PromoCode.code == code))
    if existing.scalar_one_or_none() is not None:
        raise PromoError("Такой промокод уже существует.")
    promo = PromoCode(code=code, stars=stars, max_uses=max_uses)
    session.add(promo)
    await session.commit()
    return promo


async def list_promos(session: AsyncSession) -> list[PromoCode]:
    res = await session.execute(select(PromoCode).order_by(PromoCode.id))
    return list(res.scalars().all())


async def delete_promo(session: AsyncSession, promo_id: int) -> bool:
    promo = await session.get(PromoCode, promo_id)
    if promo is None:
        return False
    await session.delete(promo)
    await session.commit()
    return True


async def redeem_promo(session: AsyncSession, user_id: int, code: str) -> PromoCode:
    code = code.strip()
    res = await session.execute(
        select(PromoCode).where(PromoCode.code == code, PromoCode.active.is_(True))
    )
    promo = res.scalar_one_or_none()
    if promo is None:
        raise PromoError("Промокод не найден.")
    used = await session.execute(
        select(PromoUse).where(PromoUse.user_id == user_id, PromoUse.promo_id == promo.id)
    )
    if used.scalar_one_or_none() is not None:
        raise PromoError("Вы уже использовали этот промокод.")
    if promo.max_uses and promo.used_count >= promo.max_uses:
        raise PromoError("Лимит использований промокода исчерпан.")
    user = await session.get(User, user_id)
    if user is None:
        raise PromoError("Пользователь не найден.")
    reward = promo.stars * 10
    user.balance_tenths += reward
    user.total_earned_tenths += reward
    promo.used_count += 1
    session.add(PromoUse(user_id=user_id, promo_id=promo.id))
    await session.commit()
    if promo.max_uses and promo.used_count >= promo.max_uses:
        await session.delete(promo)
        await session.commit()
    return promo
