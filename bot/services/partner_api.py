from __future__ import annotations

from aiohttp import web

from ..db.models import TaskItem
from .tasks import complete_task


def create_partner_app(session_factory, api_key: str) -> web.Application:
    app = web.Application()

    async def confirm(request: web.Request) -> web.Response:
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "bad_json"}, status=400)

        if data.get("api_key") != api_key:
            return web.json_response({"ok": False, "error": "forbidden"}, status=403)

        try:
            user_id = int(data["user_id"])
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
