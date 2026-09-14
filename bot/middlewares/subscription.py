from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject

from ..keyboards.user import sponsor_gate_kb
from ..services.subscriptions import missing_sponsors


def should_skip_gate(event: TelegramObject, admin_ids) -> bool:
    user = getattr(event, "from_user", None)
    if user is not None and user.id in admin_ids:
        return True
    text = getattr(event, "text", None)
    if text and text.startswith("/start"):
        return True
    data = getattr(event, "data", None)
    if data and (data == "check_subs" or data.startswith("admin:") or data.startswith("wd:paid:")):
        return True
    return False


class SubscriptionMiddleware(BaseMiddleware):
    def __init__(self, admin_ids):
        self.admin_ids = set(admin_ids)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if should_skip_gate(event, self.admin_ids):
            return await handler(event, data)

        session = data["session"]
        bot = data["bot"]
        user = event.from_user
        missing = await missing_sponsors(session, bot, user.id)
        if not missing:
            return await handler(event, data)

        text = (
            "🔒 Чтобы пользоваться ботом, подпишитесь на спонсоров ниже "
            "и нажмите «Проверить подписку»."
        )
        kb = sponsor_gate_kb(missing)
        if isinstance(event, CallbackQuery):
            await event.message.answer(text, reply_markup=kb)
            await event.answer()
        else:
            await event.answer(text, reply_markup=kb)
        return None
