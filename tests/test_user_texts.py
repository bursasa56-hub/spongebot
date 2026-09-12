from bot.db.models import User
from bot.handlers.user import profile_text


def test_profile_text_contains_stats():
    user = User(
        id=1,
        username="u",
        first_name="U",
        balance_tenths=35,
        total_earned_tenths=80,
        total_withdrawn_tenths=45,
    )
    text = profile_text(user, "my_bot", 2)
    assert "3.5 ★" in text
    assert "my_bot" in text
    assert "2" in text
