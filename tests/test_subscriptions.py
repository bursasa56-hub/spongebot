from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from bot.db.models import UserSponsor
from bot.services.referral import register_user
from bot.services.subscriptions import (
    SponsorError,
    add_bot_sponsor,
    add_channel_sponsor,
    active_sponsors,
    all_sponsors,
    delete_sponsor,
    mark_sponsor_done,
    missing_sponsors,
    needs_referral_captcha,
    parse_chat_ref,
)
from tests.fakes import FakeBot, FakeChat


def test_parse_chat_ref_variants():
    assert parse_chat_ref("@my_channel") == "@my_channel"
    assert parse_chat_ref("https://t.me/my_channel") == "@my_channel"
    assert parse_chat_ref("t.me/my_channel/12") == "@my_channel"
    assert parse_chat_ref("-1001234567890") == "-1001234567890"


def test_parse_chat_ref_invalid():
    with pytest.raises(SponsorError):
        parse_chat_ref("https://t.me/+InviteHash")


@pytest.mark.asyncio
async def test_add_channel_sponsor_requires_bot_admin(session):
    bot = FakeBot(member_status="member", chat=FakeChat(-100, "Chan", "chan"))
    with pytest.raises(SponsorError):
        await add_channel_sponsor(session, bot, "@chan")


@pytest.mark.asyncio
async def test_add_channel_sponsor_success_and_no_duplicates(session):
    bot = FakeBot(member_status="administrator", chat=FakeChat(-100, "Chan", "chan"))
    sponsor = await add_channel_sponsor(session, bot, "@chan")
    assert sponsor.chat_id == "-100"
    assert sponsor.type == "channel"
    with pytest.raises(SponsorError):
        await add_channel_sponsor(session, bot, "@chan")


@pytest.mark.asyncio
async def test_add_bot_sponsor(session):
    sponsor = await add_bot_sponsor(session, "https://t.me/partner_bot")
    assert sponsor.type == "bot"
    assert sponsor.url == "https://t.me/partner_bot"
    assert sponsor.api_key


@pytest.mark.asyncio
async def test_missing_sponsors_channel_membership(session):
    admin_bot = FakeBot(
        member_status="administrator", chat=FakeChat(-100, "Chan", "chan")
    )
    await add_channel_sponsor(session, admin_bot, "@chan")

    bot_ok = FakeBot(member_status="member")
    assert await missing_sponsors(session, bot_ok, 1) == []

    bot_no = FakeBot(raise_member=True)
    assert len(await missing_sponsors(session, bot_no, 1)) == 1


@pytest.mark.asyncio
async def test_bot_sponsor_requires_partner_confirmation(session):
    sponsor = await add_bot_sponsor(session, "@partner_bot")
    bot = FakeBot(member_status="member")

    missing = await missing_sponsors(session, bot, 1)
    assert [s.id for s in missing] == [sponsor.id]
    assert bot.member_calls == []

    assert await mark_sponsor_done(session, 1, sponsor.id) is True
    assert await missing_sponsors(session, bot, 1) == []
    assert bot.member_calls == []
    assert await mark_sponsor_done(session, 1, sponsor.id) is False


@pytest.mark.asyncio
async def test_add_channel_sponsor_private_uses_invite_link(session):
    chat = FakeChat(-100, "Private", None)
    bot = FakeBot(
        member_status="administrator",
        chat=chat,
        invite_link="https://t.me/+abc",
    )
    sponsor = await add_channel_sponsor(session, bot, "-100")
    assert sponsor.chat_id == "-100"
    assert sponsor.url == "https://t.me/+abc"


@pytest.mark.asyncio
async def test_add_channel_sponsor_private_invite_failure(session):
    chat = FakeChat(-100, "Private", None)
    bot = FakeBot(
        member_status="administrator", chat=chat, raise_invite=True
    )
    with pytest.raises(SponsorError):
        await add_channel_sponsor(session, bot, "-100")


@pytest.mark.asyncio
async def test_add_channel_sponsor_default_public_subtype(session):
    bot = FakeBot(member_status="administrator", chat=FakeChat(-100, "Chan", "chan"))
    sponsor = await add_channel_sponsor(session, bot, "@chan")
    assert sponsor.subtype == "public_channel"
    assert sponsor.url == "https://t.me/chan"
    assert bot.invite_calls == []


@pytest.mark.asyncio
async def test_add_channel_sponsor_private_request_join_link(session):
    chat = FakeChat(-100, "Private", None)
    bot = FakeBot(
        member_status="administrator", chat=chat, invite_link="https://t.me/+jr"
    )
    sponsor = await add_channel_sponsor(
        session, bot, "-100", subtype="private_request"
    )
    assert sponsor.subtype == "private_request"
    assert sponsor.url == "https://t.me/+jr"
    assert bot.invite_calls == [(-100, True)]


@pytest.mark.asyncio
async def test_private_request_missing_until_recorded_then_satisfied(session):
    chat = FakeChat(-100, "Private", None)
    admin_bot = FakeBot(member_status="administrator", chat=chat)
    sponsor = await add_channel_sponsor(
        session, admin_bot, "-100", subtype="private_request"
    )

    raising_bot = FakeBot(raise_member=True)
    assert [s.id for s in await missing_sponsors(session, raising_bot, 5)] == [sponsor.id]

    assert await mark_sponsor_done(session, 5, sponsor.id) is True
    calls_before = list(raising_bot.member_calls)
    assert await missing_sponsors(session, raising_bot, 5) == []
    assert raising_bot.member_calls == calls_before


@pytest.mark.asyncio
async def test_delete_sponsor(session):
    sponsor = await add_bot_sponsor(session, "@partner_bot")
    assert await delete_sponsor(session, sponsor.id) is True
    assert await active_sponsors(session) == []


@pytest.mark.asyncio
async def test_expired_sponsor_excluded(session):
    sponsor = await add_bot_sponsor(session, "@partner_bot")
    sponsor.expires_at = datetime.utcnow() - timedelta(hours=1)
    await session.commit()
    assert await active_sponsors(session) == []


@pytest.mark.asyncio
async def test_quota_reached_sponsor_excluded(session):
    sponsor = await add_bot_sponsor(session, "@partner_bot")
    sponsor.max_completions = 1
    await session.commit()
    assert [s.id for s in await active_sponsors(session)] == [sponsor.id]
    assert await mark_sponsor_done(session, 1, sponsor.id) is True
    assert await active_sponsors(session) == []


@pytest.mark.asyncio
async def test_channel_completion_recorded(session):
    admin_bot = FakeBot(
        member_status="administrator", chat=FakeChat(-100, "Chan", "chan")
    )
    sponsor = await add_channel_sponsor(session, admin_bot, "@chan")

    bot_ok = FakeBot(member_status="member")
    assert await missing_sponsors(session, bot_ok, 1) == []

    res = await session.execute(
        select(UserSponsor).where(
            UserSponsor.user_id == 1, UserSponsor.sponsor_id == sponsor.id
        )
    )
    assert res.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_all_sponsors_includes_expired_and_quota_reached(session):
    expired = await add_bot_sponsor(session, "@expired_bot")
    expired.expires_at = datetime.utcnow() - timedelta(hours=1)
    await session.commit()

    quota = await add_bot_sponsor(session, "@quota_bot")
    quota.max_completions = 1
    await session.commit()
    assert await mark_sponsor_done(session, 1, quota.id) is True

    assert await active_sponsors(session) == []

    ids = [s.id for s in await all_sponsors(session)]
    assert ids == [expired.id, quota.id]


@pytest.mark.asyncio
async def test_needs_referral_captcha_true_without_sponsors(session):
    await register_user(session, 1, "owner", "Owner")
    friend = await register_user(session, 2, "friend", "Friend", ref_id=1)
    assert await needs_referral_captcha(session, friend) is True


@pytest.mark.asyncio
async def test_needs_referral_captcha_false_when_sponsor_exists(session):
    await register_user(session, 1, "owner", "Owner")
    friend = await register_user(session, 2, "friend", "Friend", ref_id=1)
    await add_bot_sponsor(session, "@partner_bot")
    assert await needs_referral_captcha(session, friend) is False


@pytest.mark.asyncio
async def test_needs_referral_captcha_false_when_credited(session):
    await register_user(session, 1, "owner", "Owner")
    friend = await register_user(session, 2, "friend", "Friend", ref_id=1)
    friend.referral_credited = True
    await session.commit()
    assert await needs_referral_captcha(session, friend) is False
