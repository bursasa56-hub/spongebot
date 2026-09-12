import pytest
from aiohttp.test_utils import TestClient, TestServer

from bot.db.models import Sponsor, TaskItem, User
from bot.db.session import make_session_factory
from bot.services.partner_api import create_partner_app
from bot.services.partners import create_partner


@pytest.mark.asyncio
async def test_partner_confirm_flow(engine, session):
    session.add(User(id=5, username="u", first_name="U"))
    partner = await create_partner(session, "P")
    task = TaskItem(
        type="bot",
        title="B",
        url="https://t.me/b",
        active=True,
        partner_id=partner.id,
    )
    session.add(task)
    await session.commit()
    task_id = task.id
    key = partner.api_key

    factory = make_session_factory(engine)
    app = create_partner_app(factory)
    client = TestClient(TestServer(app))
    await client.start_server()

    bad = await client.post(
        "/partner/confirm",
        json={"api_key": "wrong", "user_id": 5, "task_id": task_id},
    )
    assert bad.status == 403

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
    partner = await create_partner(session, "P")
    sponsor = Sponsor(
        type="bot", title="@b", url="https://t.me/b", partner_id=partner.id
    )
    session.add(sponsor)
    await session.commit()
    sponsor_id = sponsor.id
    key = partner.api_key

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
    partner = await create_partner(session, "P")
    key = partner.api_key

    factory = make_session_factory(engine)
    app = create_partner_app(factory)
    client = TestClient(TestServer(app))
    await client.start_server()

    resp = await client.post(
        "/partner/confirm", json={"api_key": key, "user_id": 5}
    )
    assert resp.status == 400

    await client.close()


@pytest.mark.asyncio
async def test_partner_confirm_unknown_key(engine, session):
    session.add(User(id=5, username="u", first_name="U"))
    task = TaskItem(type="bot", title="B", url="https://t.me/b", active=True)
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
    assert resp.status == 403

    await client.close()


@pytest.mark.asyncio
async def test_partner_cannot_confirm_other_partners_resources(engine, session):
    session.add(User(id=5, username="u", first_name="U"))
    partner_a = await create_partner(session, "A")
    partner_b = await create_partner(session, "B")
    task = TaskItem(
        type="bot",
        title="TA",
        url="https://t.me/ta",
        active=True,
        partner_id=partner_a.id,
    )
    sponsor = Sponsor(
        type="bot",
        title="@sa",
        url="https://t.me/sa",
        partner_id=partner_a.id,
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
        json={"api_key": partner_a.api_key, "user_id": 5, "task_id": task_id},
    )
    assert own_task.status == 200
    assert (await own_task.json())["credited"] is True

    other_task = await client.post(
        "/partner/confirm",
        json={"api_key": partner_b.api_key, "user_id": 5, "task_id": task_id},
    )
    assert other_task.status == 404
    assert (await other_task.json())["error"] == "task_not_found"

    other_sponsor = await client.post(
        "/partner/confirm",
        json={"api_key": partner_b.api_key, "user_id": 5, "sponsor_id": sponsor_id},
    )
    assert other_sponsor.status == 404
    assert (await other_sponsor.json())["error"] == "sponsor_not_found"

    missing_user = await client.post(
        "/partner/confirm",
        json={"api_key": partner_a.api_key, "user_id": 999, "sponsor_id": sponsor_id},
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
