from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject


class IsAdmin(BaseFilter):
    def __init__(self, admin_ids):
        self.admin_ids = set(admin_ids)

    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        return user is not None and user.id in self.admin_ids
