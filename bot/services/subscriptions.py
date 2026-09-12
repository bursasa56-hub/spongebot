from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Sponsor

MEMBER_STATUSES = {"creator", "administrator", "member", "restricted"}


class SponsorError(Exception):
    pass


def parse_chat_ref(text: str) -> str:
    text = text.strip()
    if text.lstrip("-").isdigit():
        return text
    if "t.me/" in text:
        slug = text.split("t.me/", 1)[1].split("/")[0].split("?")[0]
    elif text.startswith("@"):
        slug = text[1:]
    else:
        slug = text
    if not slug or slug.startswith("+"):
        raise SponsorError(
            "Не удалось распознать ссылку. Отправьте @username, ссылку t.me/... или id -100..."
        )
    return "@" + slug


async def is_member(bot, chat_ref: str, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=chat_ref, user_id=user_id)
    except Exception:
        return False
    return getattr(member, "status", None) in MEMBER_STATUSES


async def active_sponsors(session: AsyncSession) -> list[Sponsor]:
    res = await session.execute(
        select(Sponsor).where(Sponsor.active.is_(True)).order_by(Sponsor.id)
    )
    return list(res.scalars().all())


async def missing_sponsors(session: AsyncSession, bot, user_id: int) -> list[Sponsor]:
    missing = []
    for sponsor in await active_sponsors(session):
        if not await is_member(bot, sponsor.chat_id or sponsor.url, user_id):
            missing.append(sponsor)
    return missing


async def add_channel_sponsor(session: AsyncSession, bot, link: str) -> Sponsor:
    chat_ref = parse_chat_ref(link)
    try:
        chat = await bot.get_chat(chat_ref)
    except Exception as exc:
        raise SponsorError(
            "Не удалось получить канал. Проверьте ссылку и что бот добавлен в канал."
        ) from exc

    try:
        me = await bot.get_chat_member(chat_id=chat.id, user_id=bot.id)
    except Exception as exc:
        raise SponsorError(
            "Бот не администратор этого канала. Добавьте бота в админы и повторите."
        ) from exc
    if getattr(me, "status", None) not in {"administrator", "creator"}:
        raise SponsorError(
            "Бот не администратор этого канала. Добавьте бота в админы и повторите."
        )

    existing = await session.execute(
        select(Sponsor).where(Sponsor.chat_id == str(chat.id))
    )
    if existing.scalar_one_or_none() is not None:
        raise SponsorError("Этот канал уже добавлен.")

    title = getattr(chat, "title", None) or chat_ref
    username = getattr(chat, "username", None)
    url = f"https://t.me/{username}" if username else str(chat.id)
    sponsor = Sponsor(type="channel", title=title, url=url, chat_id=str(chat.id))
    session.add(sponsor)
    await session.commit()
    return sponsor


async def add_bot_sponsor(session: AsyncSession, link: str) -> Sponsor:
    chat_ref = parse_chat_ref(link)
    username = chat_ref.lstrip("@")
    url = f"https://t.me/{username}"
    existing = await session.execute(select(Sponsor).where(Sponsor.url == url))
    if existing.scalar_one_or_none() is not None:
        raise SponsorError("Этот бот уже добавлен.")
    sponsor = Sponsor(type="bot", title="@" + username, url=url, chat_id=None)
    session.add(sponsor)
    await session.commit()
    return sponsor


async def delete_sponsor(session: AsyncSession, sponsor_id: int) -> bool:
    sponsor = await session.get(Sponsor, sponsor_id)
    if sponsor is None:
        return False
    await session.delete(sponsor)
    await session.commit()
    return True
