from bot.config import Config
from bot.main import build_dispatcher


def _config():
    return Config(
        bot_token="1:x",
        admin_ids=(1,),
        admin_chat_id=-100,
        support_url="https://t.me/s",
        db_path=":memory:",
        database_url=None,
        partner_api_host="127.0.0.1",
        partner_api_port=8080,
    )


async def test_build_dispatcher_registers_routers(engine):
    from bot.db.session import make_session_factory

    dp = build_dispatcher(_config(), make_session_factory(engine))
    assert dp is not None
    assert dp.workflow_data["support_url"] == "https://t.me/s"
    assert dp.workflow_data["admin_ids"] == {1}
