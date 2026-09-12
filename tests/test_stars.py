from bot.utils.stars import format_stars, stars_to_tenths


def test_format_whole():
    assert format_stars(30) == "3 ★"


def test_format_fraction():
    assert format_stars(5) == "0.5 ★"
    assert format_stars(35) == "3.5 ★"


def test_stars_to_tenths():
    assert stars_to_tenths(0.5) == 5
    assert stars_to_tenths(3) == 30
    assert stars_to_tenths(15) == 150
