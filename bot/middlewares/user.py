from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from ..services.referral import register_user


class UserRegisterMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        session = data.get("session")
        user = getattr(event, "from_user", None)
        if session is not None and user is not None and not getattr(user, "is_bot", False):
            await register_user(session, user.id, user.username, user.first_name)
        return await handler(event, data)
