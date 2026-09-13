from bot.config import load_config


def test_load_config(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123:abc")
    monkeypatch.setenv("ADMIN_IDS", "1, 2 ,3")
    monkeypatch.setenv("ADMIN_CHAT_ID", "-100")
    monkeypatch.setenv("SUPPORT_URL", "https://t.me/sup")
    monkeypatch.setenv("DB_PATH", "data/x.db")
    monkeypatch.setenv("PARTNER_API_PORT", "9090")

    cfg = load_config(None)

    assert cfg.bot_token == "123:abc"
    assert cfg.admin_ids == (1, 2, 3)
    assert cfg.admin_chat_id == -100
    assert cfg.support_url == "https://t.me/sup"
    assert cfg.db_path == "data/x.db"
    assert cfg.partner_api_port == 9090
    assert cfg.partner_api_host == "0.0.0.0"


def test_port_env_fallback(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123:abc")
    monkeypatch.setenv("ADMIN_CHAT_ID", "-100")
    monkeypatch.delenv("PARTNER_API_PORT", raising=False)
    monkeypatch.setenv("PORT", "5000")

    cfg = load_config(None)

    assert cfg.partner_api_port == 5000
