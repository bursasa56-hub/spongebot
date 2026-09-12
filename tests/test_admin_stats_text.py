from bot.handlers.admin import stats_text
from bot.services.stats import Stats


def test_stats_text_contains_month():
    stats = Stats(
        total_users=10,
        new_today=2,
        new_week=5,
        new_month=7,
        referrals=4,
        earned_tenths=300,
        withdrawn_tenths=150,
        pending_withdrawals=1,
        tasks_done=8,
    )
    text = stats_text(stats)
    assert "за месяц" in text.lower()
    assert "10" in text
    assert "30 ★" in text
