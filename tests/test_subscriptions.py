import pytest

from bot.services.subscriptions import (
    SponsorError,
    add_bot_sponsor,
    add_channel_sponsor,
    active_sponsors,
    delete_sponsor,
    mark_sponsor_done,
    missing_sponsors,
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
async def test_delete_sponsor(session):
    sponsor = await add_bot_sponsor(session, "@partner_bot")
    assert await delete_sponsor(session, sponsor.id) is True
    assert await active_sponsors(session) == []
