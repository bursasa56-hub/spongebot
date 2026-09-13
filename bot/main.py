from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web

from .config import Config, load_config
from .db.session import create_engine, ensure_db_dir, init_db, make_session_factory
from .handlers.admin import router_admin
from .handlers.join_requests import router_join
from .handlers.promo import router_promo
from .handlers.start import router_start
from .handlers.tasks import router_tasks
from .handlers.user import router_user
from .handlers.withdraw import router_withdraw
from .middlewares.db import DbSessionMiddleware
from .middlewares.subscription import SubscriptionMiddleware
from .services.partner_api import create_partner_app

logging.basicConfig(level=logging.INFO)


def build_dispatcher(config: Config, session_factory) -> Dispatcher:
    dp = Dispatcher()
    for observer in (dp.message, dp.callback_query):
        observer.middleware(DbSessionMiddleware(session_factory))
        observer.middleware(SubscriptionMiddleware(config.admin_ids))
    dp.chat_join_request.middleware(DbSessionMiddleware(session_factory))

    dp.workflow_data["support_url"] = config.support_url
    dp.workflow_data["config"] = config
    dp.workflow_data["admin_ids"] = set(config.admin_ids)

    dp.include_router(router_admin)
    dp.include_router(router_start)
    dp.include_router(router_user)
    dp.include_router(router_tasks)
    dp.include_router(router_promo)
    dp.include_router(router_join)
    dp.include_router(router_withdraw)
    return dp


async def main() -> None:
    config = load_config()
    if not config.database_url:
        ensure_db_dir(config.db_path)
    engine = create_engine(config.db_path, config.database_url)
    await init_db(engine)
    session_factory = make_session_factory(engine)

    bot = Bot(
        config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = build_dispatcher(config, session_factory)

    app = create_partner_app(session_factory)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.partner_api_host, config.partner_api_port)
    await site.start()

    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
