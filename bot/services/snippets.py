from __future__ import annotations

import json


def build_snippet(
    api_base_url: str | None,
    api_key: str | None,
    *,
    task_id: int | None = None,
    sponsor_id: int | None = None,
) -> str:
    base = (api_base_url or "<ВАШ_АДРЕС>").rstrip("/")
    url = f"{base}/partner/confirm"
    key = api_key or "<КЛЮЧ_ПАРТНЁРА>"
    if task_id is not None:
        id_name, id_value = "task_id", task_id
    else:
        id_name, id_value = "sponsor_id", sponsor_id
    payload = json.dumps(
        {"api_key": key, "user_id": 123, id_name: id_value}, ensure_ascii=False
    )
    return (
        f"# Партнёрская интеграция ({id_name}={id_value})\n"
        "import aiohttp\n\n"
        f'API_URL = "{url}"\n'
        f'API_KEY = "{key}"\n\n'
        "async def report_start(user_id: int) -> None:\n"
        "    async with aiohttp.ClientSession() as session:\n"
        "        await session.post(\n"
        "            API_URL,\n"
        '            json={"api_key": API_KEY, "user_id": user_id, '
        f'"{id_name}": {id_value}}},\n'
        "        )\n\n"
        "# curl:\n"
        f"# curl -X POST {url} -H \"Content-Type: application/json\" -d '{payload}'\n"
    )
