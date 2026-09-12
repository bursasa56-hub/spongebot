from bot.middlewares.subscription import should_skip_gate


class FakeUser:
    def __init__(self, uid):
        self.id = uid


class FakeMessage:
    def __init__(self, text, uid=1):
        self.text = text
        self.from_user = FakeUser(uid)


class FakeCallback:
    def __init__(self, data, uid=1):
        self.data = data
        self.from_user = FakeUser(uid)


def test_skip_start_and_gate_callbacks():
    assert should_skip_gate(FakeMessage("/start"), {}) is True
    assert should_skip_gate(FakeCallback("check_subs"), {}) is True
    assert should_skip_gate(FakeCallback("admin:menu"), {}) is True
    assert should_skip_gate(FakeMessage("привет"), {}) is False


def test_admins_skip_gate():
    assert should_skip_gate(FakeMessage("hi", uid=7), {7}) is True
    assert should_skip_gate(FakeMessage("hi", uid=8), {7}) is False
