import pytest

from bot.db.models import TaskItem, User
from bot.handlers.tasks import next_task, show_tasks
from bot.services.tasks import complete_task


class FakeMessage:
    def __init__(self):
        self.answers = []
        self.edits = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))

    async def edit_text(self, text, **kwargs):
        self.edits.append((text, kwargs))


class FakeCallback:
    def __init__(self, data="", user_id=1):
        self.data = data
        self.from_user = type("U", (), {"id": user_id})()
        self.message = FakeMessage()
        self.answered = False

    async def answer(self, *args, **kwargs):
        self.answered = True


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


@pytest.mark.asyncio
async def test_show_tasks_sends_new_message_with_count(session):
    session.add(User(id=1, username="u", first_name="U"))
    task = TaskItem(type="channel", title="T1", url="u1", chat_id="@t1")
    session.add(task)
    await session.commit()
    callback = FakeCallback("menu:tasks", user_id=1)

    await show_tasks(callback, session)

    assert callback.answered is True
    assert callback.message.edits == []
    assert callback.message.answers
    text = callback.message.answers[-1][0]
    assert "доступно" in text
    assert "доступно: 1" in text
