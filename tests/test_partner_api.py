import pytest
from aiohttp.test_utils import TestClient, TestServer

from bot.db.models import Sponsor, TaskItem, User
from bot.db.session import make_session_factory
from bot.services.partner_api import create_partner_app


@pytest.mark.asyncio
async def test_partner_confirm_flow(engine, session):
    session.add(User(id=5, username="u", first_name="U"))
    task = TaskItem(
        type="bot",
        title="B",
        url="https://t.me/b",
        active=True,
        api_key="secret",
    )
    session.add(task)
    await session.commit()
    task_id = task.id
    key = "secret"

    factory = make_session_factory(engine)
    app = create_partner_app(factory)
    client = TestClient(TestServer(app))
    await client.start_server()

    bad = await client.post(
        "/partner/confirm",
        json={"api_key": "wrong", "user_id": 5, "task_id": task_id},
    )
    assert bad.status == 404

    ok = await client.post(
        "/partner/confirm",
        json={"api_key": key, "user_id": 5, "task_id": task_id},
    )
    assert ok.status == 200
    body = await ok.json()
    assert body["credited"] is True

    again = await client.post(
        "/partner/confirm",
        json={"api_key": key, "user_id": 5, "task_id": task_id},
    )
    assert (await again.json())["credited"] is False

    await client.close()


@pytest.mark.asyncio
async def test_partner_confirm_sponsor(engine, session):
    session.add(User(id=5, username="u", first_name="U"))
    sponsor = Sponsor(
        type="bot", title="@b", url="https://t.me/b", api_key="secret"
    )
    session.add(sponsor)
    await session.commit()
    sponsor_id = sponsor.id
    key = "secret"

    factory = make_session_factory(engine)
    app = create_partner_app(factory)
    client = TestClient(TestServer(app))
    await client.start_server()

    ok = await client.post(
        "/partner/confirm",
        json={"api_key": key, "user_id": 5, "sponsor_id": sponsor_id},
    )
    assert ok.status == 200
    assert (await ok.json())["credited"] is True

    again = await client.post(
        "/partner/confirm",
        json={"api_key": key, "user_id": 5, "sponsor_id": sponsor_id},
    )
    assert (await again.json())["credited"] is False

    await client.close()


@pytest.mark.asyncio
async def test_partner_confirm_requires_target(engine, session):
    session.add(User(id=5, username="u", first_name="U"))
    await session.commit()

    factory = make_session_factory(engine)
    app = create_partner_app(factory)
    client = TestClient(TestServer(app))
    await client.start_server()

    resp = await client.post(
        "/partner/confirm", json={"api_key": "secret", "user_id": 5}
    )
    assert resp.status == 400

    await client.close()


@pytest.mark.asyncio
async def test_partner_confirm_missing_key(engine, session):
    session.add(User(id=5, username="u", first_name="U"))
    task = TaskItem(
        type="bot", title="B", url="https://t.me/b", active=True, api_key="secret"
    )
    session.add(task)
    await session.commit()
    task_id = task.id

    factory = make_session_factory(engine)
    app = create_partner_app(factory)
    client = TestClient(TestServer(app))
    await client.start_server()

    resp = await client.post(
        "/partner/confirm", json={"user_id": 5, "task_id": task_id}
    )
    assert resp.status == 403

    await client.close()


@pytest.mark.asyncio
async def test_partner_confirm_unknown_key(engine, session):
    session.add(User(id=5, username="u", first_name="U"))
    task = TaskItem(
        type="bot", title="B", url="https://t.me/b", active=True, api_key="secret"
    )
    session.add(task)
    await session.commit()
    task_id = task.id

    factory = make_session_factory(engine)
    app = create_partner_app(factory)
    client = TestClient(TestServer(app))
    await client.start_server()

    resp = await client.post(
        "/partner/confirm",
        json={"api_key": "unknown", "user_id": 5, "task_id": task_id},
    )
    assert resp.status == 404
    assert (await resp.json())["error"] == "task_not_found"

    await client.close()


@pytest.mark.asyncio
async def test_partner_cannot_confirm_other_resources(engine, session):
    session.add(User(id=5, username="u", first_name="U"))
    task = TaskItem(
        type="bot",
        title="TA",
        url="https://t.me/ta",
        active=True,
        api_key="secret_a",
    )
    sponsor = Sponsor(
        type="bot",
        title="@sa",
        url="https://t.me/sa",
        api_key="secret_a",
    )
    session.add_all([task, sponsor])
    await session.commit()
    task_id = task.id
    sponsor_id = sponsor.id

    factory = make_session_factory(engine)
    app = create_partner_app(factory)
    client = TestClient(TestServer(app))
    await client.start_server()

    own_task = await client.post(
        "/partner/confirm",
        json={"api_key": "secret_a", "user_id": 5, "task_id": task_id},
    )
    assert own_task.status == 200
    assert (await own_task.json())["credited"] is True

    other_task = await client.post(
        "/partner/confirm",
        json={"api_key": "secret_b", "user_id": 5, "task_id": task_id},
    )
    assert other_task.status == 404
    assert (await other_task.json())["error"] == "task_not_found"

    other_sponsor = await client.post(
        "/partner/confirm",
        json={"api_key": "secret_b", "user_id": 5, "sponsor_id": sponsor_id},
    )
    assert other_sponsor.status == 404
    assert (await other_sponsor.json())["error"] == "sponsor_not_found"

    missing_user = await client.post(
        "/partner/confirm",
        json={"api_key": "secret_a", "user_id": 999, "sponsor_id": sponsor_id},
    )
    assert missing_user.status == 404
    assert (await missing_user.json())["error"] == "user_not_found"

    await client.close()


@pytest.mark.asyncio
async def test_health_endpoint(engine):
    factory = make_session_factory(engine)
    app = create_partner_app(factory)
    client = TestClient(TestServer(app))
    await client.start_server()

    resp = await client.get("/health")
    assert resp.status == 200
    assert (await resp.json())["ok"] is True

    await client.close()
