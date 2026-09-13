import pytest
from sqlalchemy import select

from bot.db.models import TaskItem, User, UserSponsor, UserTask
from bot.handlers.join_requests import on_join_request
from bot.services.subscriptions import add_channel_sponsor
from tests.fakes import FakeBot, FakeChat


class FakeJoinRequest:
    def __init__(self, chat_id=-100, user_id=5):
        self.chat = type("Chat", (), {"id": chat_id})()
        self.from_user = type("User", (), {"id": user_id})()


@pytest.mark.asyncio
async def test_join_request_records_sponsor_done(session):
    chat = FakeChat(-100, "Private", None)
    bot = FakeBot(member_status="administrator", chat=chat)
    sponsor = await add_channel_sponsor(
        session, bot, "-100", subtype="private_request"
    )

    await on_join_request(FakeJoinRequest(chat_id=-100, user_id=5), session)

    res = await session.execute(
        select(UserSponsor).where(
            UserSponsor.user_id == 5, UserSponsor.sponsor_id == sponsor.id
        )
    )
    assert res.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_join_request_completes_private_channel_task(session):
    session.add(User(id=5, username="u", first_name="U"))
    task = TaskItem(
        type="channel",
        subtype="private_request",
        title="Private task",
        url="https://t.me/+invite",
        chat_id="-100",
        reward_tenths=5,
    )
    session.add(task)
    await session.commit()
    task_id = task.id

    await on_join_request(FakeJoinRequest(chat_id=-100, user_id=5), session)

    res = await session.execute(
        select(UserTask).where(
            UserTask.user_id == 5, UserTask.task_id == task_id
        )
    )
    assert res.scalar_one_or_none() is not None
    user = await session.get(User, 5)
    assert user.balance_tenths == 5


@pytest.mark.asyncio
async def test_join_request_unknown_chat_is_ignored(session):
    await on_join_request(FakeJoinRequest(chat_id=-555, user_id=5), session)
    assert (await session.execute(select(UserSponsor))).scalars().all() == []
