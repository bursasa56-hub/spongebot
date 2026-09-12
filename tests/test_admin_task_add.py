import pytest

from bot.db.models import TaskItem
from bot.services.tasks import available_tasks


@pytest.mark.asyncio
async def test_added_channel_task_is_available(session):
    from bot.db.models import User

    session.add(User(id=1, username="u", first_name="U"))
    session.add(
        TaskItem(type="channel", title="Подпишись", url="https://t.me/x", chat_id="@x")
    )
    await session.commit()
    assert len(await available_tasks(session, 1)) == 1
