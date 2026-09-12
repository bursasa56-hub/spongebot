from __future__ import annotations

from aiohttp import web

from ..db.models import Sponsor, TaskItem
from .partners import verify_key
from .subscriptions import mark_sponsor_done
from .tasks import complete_task


def create_partner_app(session_factory) -> web.Application:
    app = web.Application()

    async def confirm(request: web.Request) -> web.Response:
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "bad_json"}, status=400)

        async with session_factory() as session:
            partner = await verify_key(session, data.get("api_key"))
        if partner is None:
            return web.json_response({"ok": False, "error": "forbidden"}, status=403)

        has_task = data.get("task_id") is not None
        has_sponsor = data.get("sponsor_id") is not None
        if not has_task and not has_sponsor:
            return web.json_response({"ok": False, "error": "bad_payload"}, status=400)

        try:
            user_id = int(data["user_id"])
        except (KeyError, TypeError, ValueError):
            return web.json_response({"ok": False, "error": "bad_payload"}, status=400)

        if has_sponsor:
            try:
                sponsor_id = int(data["sponsor_id"])
            except (TypeError, ValueError):
                return web.json_response({"ok": False, "error": "bad_payload"}, status=400)

            async with session_factory() as session:
                sponsor = await session.get(Sponsor, sponsor_id)
                if sponsor is None or not sponsor.active or sponsor.type != "bot":
                    return web.json_response(
                        {"ok": False, "error": "sponsor_not_found"}, status=404
                    )
                credited = await mark_sponsor_done(session, user_id, sponsor_id)
                return web.json_response({"ok": True, "credited": credited})

        try:
            task_id = int(data["task_id"])
        except (KeyError, TypeError, ValueError):
            return web.json_response({"ok": False, "error": "bad_payload"}, status=400)

        async with session_factory() as session:
            task = await session.get(TaskItem, task_id)
            if task is None or not task.active or task.type != "bot":
                return web.json_response(
                    {"ok": False, "error": "task_not_found"}, status=404
                )
            done = await complete_task(session, user_id, task_id)
            return web.json_response({"ok": True, "credited": done is not None})

    app.router.add_post("/partner/confirm", confirm)
    return app
