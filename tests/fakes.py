class FakeChat:
    def __init__(self, id, title="T", username=None):
        self.id = id
        self.title = title
        self.username = username


class FakeMember:
    def __init__(self, status):
        self.status = status


class FakeInvite:
    def __init__(self, invite_link):
        self.invite_link = invite_link


class FakeBot:
    def __init__(
        self,
        id=999,
        member_status="member",
        chat=None,
        raise_member=False,
        invite_link="https://t.me/+invite",
        raise_invite=False,
    ):
        self.id = id
        self._member_status = member_status
        self._chat = chat
        self._raise_member = raise_member
        self._invite_link = invite_link
        self._raise_invite = raise_invite
        self.member_calls = []
        self.invite_calls = []

    async def get_chat(self, chat_id):
        if self._chat is None:
            raise RuntimeError("no chat")
        return self._chat

    async def get_chat_member(self, chat_id, user_id):
        self.member_calls.append((chat_id, user_id))
        if self._raise_member:
            raise RuntimeError("not a member")
        return FakeMember(self._member_status)

    async def create_chat_invite_link(self, chat_id, creates_join_request=False):
        self.invite_calls.append((chat_id, creates_join_request))
        if self._raise_invite:
            raise RuntimeError("cannot create invite")
        return FakeInvite(self._invite_link)
