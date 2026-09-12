from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject


class IsAdmin(BaseFilter):
    async def __call__(self, event: TelegramObject, admin_ids=None) -> bool:
        if not admin_ids:
            return False
        user = getattr(event, "from_user", None)
        return user is not None and user.id in set(admin_ids)
