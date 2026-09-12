import pytest
from aiohttp.test_utils import TestClient, TestServer

from bot.db.models import TaskItem, User
from bot.db.session import make_session_factory
from bot.services.partner_api import create_partner_app


@pytest.mark.asyncio
async def test_partner_confirm_flow(engine, session):
    session.add(User(id=5, username="u", first_name="U"))
    task = TaskItem(type="bot", title="B", url="https://t.me/b", active=True)
    session.add(task)
    await session.commit()
    task_id = task.id

    factory = make_session_factory(engine)
    app = create_partner_app(factory, "secret")
    client = TestClient(TestServer(app))
    await client.start_server()

    bad = await client.post(
        "/partner/confirm",
        json={"api_key": "wrong", "user_id": 5, "task_id": task_id},
    )
    assert bad.status == 403

    ok = await client.post(
        "/partner/confirm",
        json={"api_key": "secret", "user_id": 5, "task_id": task_id},
    )
    assert ok.status == 200
    body = await ok.json()
    assert body["credited"] is True

    again = await client.post(
        "/partner/confirm",
        json={"api_key": "secret", "user_id": 5, "task_id": task_id},
    )
    assert (await again.json())["credited"] is False

    await client.close()
