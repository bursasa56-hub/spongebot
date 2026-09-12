import pytest

from bot.db.models import TaskItem, User
from bot.handlers.tasks import next_task
from bot.services.tasks import complete_task


@pytest.mark.asyncio
async def test_next_task_skips_excluded(session):
    session.add(User(id=1, username="u", first_name="U"))
    t1 = TaskItem(type="channel", title="T1", url="u1", chat_id="@t1")
    t2 = TaskItem(type="channel", title="T2", url="u2", chat_id="@t2")
    session.add_all([t1, t2])
    await session.commit()

    first = await next_task(session, 1)
    assert first.id == t1.id
    second = await next_task(session, 1, exclude_id=t1.id)
    assert second.id == t2.id
    await complete_task(session, 1, t1.id)
    await complete_task(session, 1, t2.id)
    assert await next_task(session, 1) is None
