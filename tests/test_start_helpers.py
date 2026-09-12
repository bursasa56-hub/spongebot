from bot.handlers.start import parse_ref


def test_parse_ref():
    assert parse_ref("ref_123") == 123
    assert parse_ref("/start ref_5") == 5
    assert parse_ref(None) is None
    assert parse_ref("garbage") is None
    assert parse_ref("ref_abc") is None
