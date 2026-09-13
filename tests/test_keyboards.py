from urllib.parse import quote

from bot.db.models import Partner, PromoCode, Sponsor, TaskItem
from bot.keyboards.admin import (
    admin_menu_kb,
    partner_choice_kb,
    partners_admin_kb,
    promos_admin_kb,
    sponsor_channel_subtype_kb,
    sponsor_duration_kb,
    sponsor_quota_kb,
    sponsor_type_kb,
    sponsors_admin_kb,
    task_channel_subtype_kb,
    task_type_kb,
)
from bot.keyboards.user import (
    bet_kb,
    earn_kb,
    games_menu_kb,
    gifts_kb,
    main_menu_kb,
    rps_kb,
    task_kb,
)
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


def test_gifts_kb_two_per_row_and_all_gifts():
    kb = gifts_kb()
    assert len(kb.inline_keyboard[0]) == 2
    ids = [b.callback_data for row in kb.inline_keyboard for b in row]
    assert "wd:gift:bear" in ids
    assert "wd:gift:diamond" in ids
    assert "wd:friend" in ids


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


def test_task_channel_subtype_kb_callbacks():
    data = _callbacks(task_channel_subtype_kb())
    assert "admin:task:subtype:public_channel" in data
    assert "admin:task:subtype:chat" in data
    assert "admin:task:subtype:private_request" in data


def test_admin_menu_has_promos():
    assert "admin:promos" in _callbacks(admin_menu_kb())


def test_admin_menu_has_reset_stars():
    assert "admin:reset" in _callbacks(admin_menu_kb())


def test_sponsor_channel_subtype_kb_callbacks():
    data = _callbacks(sponsor_channel_subtype_kb())
    assert "admin:sponsor:subtype:public_channel" in data
    assert "admin:sponsor:subtype:chat" in data
    assert "admin:sponsor:subtype:private_request" in data


def test_promos_admin_kb_renders_promos():
    promo = PromoCode(id=4, code="SALE", stars=5, max_uses=0, used_count=2)
    kb = promos_admin_kb([promo])
    data = _callbacks(kb)
    assert "admin:promo:add" in data
    assert "admin:promo:del:4" in data


def test_games_menu_kb_has_rps():
    assert "game:rps" in _callbacks(games_menu_kb())


def test_bet_kb_has_presets_and_custom():
    data = _callbacks(bet_kb(100))
    assert "game:bet:5" in data
    assert "game:bet:custom" in data


def test_rps_kb_has_all_moves():
    data = _callbacks(rps_kb())
    assert "game:move:rock" in data
    assert "game:move:scissors" in data
    assert "game:move:paper" in data
