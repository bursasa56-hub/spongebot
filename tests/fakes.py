class FakeChat:
    def __init__(self, id, title="T", username=None):
        self.id = id
        self.title = title
        self.username = username


class FakeMember:
    def __init__(self, status):
        self.status = status


class FakeBot:
    def __init__(self, id=999, member_status="member", chat=None, raise_member=False):
        self.id = id
        self._member_status = member_status
        self._chat = chat
        self._raise_member = raise_member

    async def get_chat(self, chat_id):
        if self._chat is None:
            raise RuntimeError("no chat")
        return self._chat

    async def get_chat_member(self, chat_id, user_id):
        if self._raise_member:
            raise RuntimeError("not a member")
        return FakeMember(self._member_status)
