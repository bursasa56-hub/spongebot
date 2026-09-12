from urllib.parse import quote

from bot.db.models import Partner, Sponsor, TaskItem
from bot.keyboards.admin import (
    admin_menu_kb,
    partner_choice_kb,
    partners_admin_kb,
    sponsor_duration_kb,
    sponsor_quota_kb,
    sponsor_type_kb,
    sponsors_admin_kb,
    task_type_kb,
)
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


def test_admin_menu_has_partners_and_settings():
    data = _callbacks(admin_menu_kb())
    assert "admin:partners" in data
    assert "admin:settings" in data


def test_partner_choice_kb_has_no_partner_option():
    kb = partner_choice_kb([], "admin:sponsor:partner")
    assert "admin:sponsor:partner:0" in _callbacks(kb)


def test_partners_admin_kb_renders_partner_row():
    partner = Partner(id=3, name="Acme", api_key="k")
    kb = partners_admin_kb([partner])
    callbacks = _callbacks(kb)
    assert "admin:partner:add" in callbacks
    assert "admin:partner:del:3" in callbacks
    assert "admin:partner:key:3" in callbacks


def test_sponsors_admin_kb_shows_id_and_code_for_bot():
    sponsor = Sponsor(id=5, type="bot", title="@bot", url="https://t.me/bot")
    kb = sponsors_admin_kb([sponsor], {5: "бессрочно"})
    texts = [b.text for row in kb.inline_keyboard for b in row]
    callbacks = _callbacks(kb)
    assert any("#5" in text for text in texts)
    assert "admin:sponsor:del:5" in callbacks
    assert "admin:sponsor:code:5" in callbacks


def test_sponsors_admin_kb_renders_status_text():
    sponsor = Sponsor(id=9, type="bot", title="@expired", url="https://t.me/expired")
    kb = sponsors_admin_kb([sponsor], {9: "истёк"})
    texts = [b.text for row in kb.inline_keyboard for b in row]
    assert any("истёк" in text for text in texts)
    assert "admin:sponsor:code:9" in _callbacks(kb)


def test_sponsors_admin_kb_has_single_add_button():
    assert "admin:sponsor:add" in _callbacks(sponsors_admin_kb([], {}))


def test_sponsor_type_kb_callbacks():
    data = _callbacks(sponsor_type_kb())
    assert "admin:sponsor:type:channel" in data
    assert "admin:sponsor:type:bot" in data


def test_sponsor_duration_kb_callbacks():
    data = _callbacks(sponsor_duration_kb())
    assert "admin:sponsor:duration:0" in data
    assert "admin:sponsor:duration:1" in data


def test_sponsor_quota_kb_callbacks():
    data = _callbacks(sponsor_quota_kb())
    assert "admin:sponsor:quota:0" in data
    assert "admin:sponsor:quota:1" in data


def test_task_type_kb_callbacks():
    data = _callbacks(task_type_kb())
    assert "admin:task:type:channel" in data
    assert "admin:task:type:bot" in data
