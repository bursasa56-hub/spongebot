from bot.utils.captcha import build_captcha


def test_build_captcha_returns_target_in_options():
    target, options = build_captcha()
    assert target in options
    assert len(options) == 4
    assert len(set(options)) == 4
