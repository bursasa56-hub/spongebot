from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: tuple[int, ...]
    admin_chat_id: int
    support_url: str
    db_path: str
    database_url: str | None
    partner_api_host: str
    partner_api_port: int


def load_config(env_file: str | None = ".env") -> Config:
    if env_file:
        load_dotenv(env_file)
    admin_ids = tuple(
        int(part) for part in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if part
    )
    return Config(
        bot_token=os.environ["BOT_TOKEN"],
        admin_ids=admin_ids,
        admin_chat_id=int(os.environ["ADMIN_CHAT_ID"]),
        support_url=os.getenv("SUPPORT_URL", "https://t.me/burfreestarssupport"),
        db_path=os.getenv("DB_PATH", "data/bot.db"),
        database_url=os.getenv("DATABASE_URL") or None,
        partner_api_host=os.getenv("PARTNER_API_HOST", "0.0.0.0"),
        partner_api_port=int(
            os.getenv("PARTNER_API_PORT") or os.getenv("PORT") or "8080"
        ),
    )
