from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Sponsor, UserSponsor

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


async def count_sponsor_completions(session: AsyncSession, sponsor_id: int) -> int:
    from sqlalchemy import func

    return (
        await session.execute(
            select(func.count())
            .select_from(UserSponsor)
            .where(UserSponsor.sponsor_id == sponsor_id)
        )
    ).scalar_one()


async def all_sponsors(session: AsyncSession) -> list[Sponsor]:
    res = await session.execute(select(Sponsor).order_by(Sponsor.id))
    return list(res.scalars().all())


async def active_sponsors(session: AsyncSession) -> list[Sponsor]:
    from datetime import datetime

    now = datetime.utcnow()
    res = await session.execute(
        select(Sponsor).where(Sponsor.active.is_(True)).order_by(Sponsor.id)
    )
    result = []
    for sponsor in res.scalars().all():
        if sponsor.expires_at is not None and sponsor.expires_at <= now:
            continue
        if sponsor.max_completions and (
            await count_sponsor_completions(session, sponsor.id) >= sponsor.max_completions
        ):
            continue
        result.append(sponsor)
    return result


async def sponsor_status(session: AsyncSession, sponsor: Sponsor) -> str:
    from datetime import datetime

    now = datetime.utcnow()
    if not sponsor.active:
        return "выключен"
    if sponsor.expires_at is not None and sponsor.expires_at <= now:
        return "истёк"
    done = await count_sponsor_completions(session, sponsor.id)
    if sponsor.max_completions and done >= sponsor.max_completions:
        return "квота исчерпана"
    parts = []
    if sponsor.expires_at is not None:
        hours = int((sponsor.expires_at - now).total_seconds() // 3600)
        parts.append(f"осталось ~{hours} ч")
    if sponsor.max_completions:
        parts.append(f"осталось {sponsor.max_completions - done}")
    return ", ".join(parts) if parts else "бессрочно"


async def missing_sponsors(session: AsyncSession, bot, user_id: int) -> list[Sponsor]:
    missing = []
    for sponsor in await active_sponsors(session):
        if sponsor.type == "bot":
            done = await session.execute(
                select(UserSponsor).where(
                    UserSponsor.user_id == user_id,
                    UserSponsor.sponsor_id == sponsor.id,
                )
            )
            if done.scalar_one_or_none() is None:
                missing.append(sponsor)
        elif not await is_member(bot, sponsor.chat_id or sponsor.url, user_id):
            missing.append(sponsor)
        else:
            await mark_sponsor_done(session, user_id, sponsor.id)
    return missing


async def mark_sponsor_done(session: AsyncSession, user_id: int, sponsor_id: int) -> bool:
    existing = await session.execute(
        select(UserSponsor).where(
            UserSponsor.user_id == user_id, UserSponsor.sponsor_id == sponsor_id
        )
    )
    if existing.scalar_one_or_none() is not None:
        return False
    session.add(UserSponsor(user_id=user_id, sponsor_id=sponsor_id))
    await session.commit()
    return True


async def add_channel_sponsor(
    session: AsyncSession,
    bot,
    link: str,
    *,
    expires_at=None,
    max_completions: int = 0,
    partner_id: int | None = None,
) -> Sponsor:
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
    if username:
        url = f"https://t.me/{username}"
    else:
        try:
            invite = await bot.create_chat_invite_link(chat.id)
        except Exception as exc:
            raise SponsorError(
                "У канала нет публичного @username и не удалось создать ссылку-приглашение."
            ) from exc
        url = invite.invite_link
    sponsor = Sponsor(
        type="channel",
        title=title,
        url=url,
        chat_id=str(chat.id),
        expires_at=expires_at,
        max_completions=max_completions,
        partner_id=partner_id,
    )
    session.add(sponsor)
    await session.commit()
    return sponsor


async def add_bot_sponsor(
    session: AsyncSession,
    link: str,
    *,
    expires_at=None,
    max_completions: int = 0,
    partner_id: int | None = None,
) -> Sponsor:
    chat_ref = parse_chat_ref(link)
    username = chat_ref.lstrip("@")
    url = f"https://t.me/{username}"
    existing = await session.execute(select(Sponsor).where(Sponsor.url == url))
    if existing.scalar_one_or_none() is not None:
        raise SponsorError("Этот бот уже добавлен.")
    sponsor = Sponsor(
        type="bot",
        title="@" + username,
        url=url,
        chat_id=None,
        expires_at=expires_at,
        max_completions=max_completions,
        partner_id=partner_id,
    )
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
