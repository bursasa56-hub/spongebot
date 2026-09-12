import pytest

from bot.db.models import TaskItem, User
from bot.services.tasks import available_tasks, complete_task


async def _make_user(session, uid=1):
    session.add(User(id=uid, username="u", first_name="U"))
    await session.commit()


@pytest.mark.asyncio
async def test_complete_task_awards_once(session):
    await _make_user(session)
    task = TaskItem(type="channel", title="T", url="https://t.me/t", chat_id="@t")
    session.add(task)
    await session.commit()

    done = await complete_task(session, 1, task.id)
    assert done is not None
    user = await session.get(User, 1)
    assert user.balance_tenths == 5

    again = await complete_task(session, 1, task.id)
    assert again is None
    assert user.balance_tenths == 5


@pytest.mark.asyncio
async def test_available_excludes_completed(session):
    await _make_user(session)
    t1 = TaskItem(type="channel", title="T1", url="u1", chat_id="@t1")
    t2 = TaskItem(type="channel", title="T2", url="u2", chat_id="@t2")
    session.add_all([t1, t2])
    await session.commit()

    assert len(await available_tasks(session, 1)) == 2
    await complete_task(session, 1, t1.id)
    remaining = await available_tasks(session, 1)
    assert [t.id for t in remaining] == [t2.id]


@pytest.mark.asyncio
async def test_inactive_task_not_completable(session):
    await _make_user(session)
    task = TaskItem(type="channel", title="T", url="u", chat_id="@t", active=False)
    session.add(task)
    await session.commit()
    assert await complete_task(session, 1, task.id) is None
