from urllib.parse import quote

from bot.db.models import Sponsor, TaskItem
from bot.keyboards.user import earn_kb, gifts_kb, main_menu_kb, task_kb
from bot.utils.gifts import FIXED_GIFTS


def _callbacks(kb):
    return [b.callback_data for row in kb.inline_keyboard for b in row]


def test_main_menu_has_all_buttons():
    data = _callbacks(main_menu_kb())
    for expected in [
        "menu:profile",
        "menu:instruction",
        "menu:tasks",
        "menu:withdraw",
        "menu:earn",
    ]:
        assert expected in data


def test_gifts_kb_only_affordable():
    kb = gifts_kb(200)
    ids = [b.callback_data for row in kb.inline_keyboard for b in row]
    assert "wd:gift:bear" in ids
    assert "wd:gift:rose" not in ids


def test_task_kb_has_check_and_skip():
    task = TaskItem(id=7, type="channel", title="T", url="u", chat_id="@t")
    data = _callbacks(task_kb(task))
    assert "task:check:7" in data
    assert "task:skip:7" in data


def test_earn_kb_url_encodes_ref_link_and_text():
    kb = earn_kb("https://t.me/my_bot?start=ref_1")
    url = kb.inline_keyboard[0][0].url
    assert " " not in url
    assert quote("https://t.me/my_bot?start=ref_1", safe="") in url
    assert quote("Заработай звёзды!") in url
