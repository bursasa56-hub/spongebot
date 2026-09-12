from bot.handlers.withdraw import normalize_username


def test_normalize_username():
    assert normalize_username("@friend") == "friend"
    assert normalize_username("friend") == "friend"
    assert normalize_username("https://t.me/friend") == "friend"
    assert normalize_username("bad name") is None
    assert normalize_username("") is None
