import pytest

from bot.db.models import User
from bot.services.games import GameError, play_rps


async def _make_user(session, uid=1, balance=1000, games_played=0):
    user = User(
        id=uid,
        username="u",
        first_name="U",
        balance_tenths=balance,
        games_played=games_played,
    )
    session.add(user)
    await session.commit()
    return user


@pytest.mark.asyncio
async def test_first_two_games_always_win(session):
    await _make_user(session, balance=1000)
    first = await play_rps(session, 1, 10, "rock")
    second = await play_rps(session, 1, 10, "rock")
    assert first["outcome"] == "win"
    assert second["outcome"] == "win"
    user = await session.get(User, 1)
    assert user.balance_tenths == 1020
    assert user.games_played == 2


@pytest.mark.asyncio
async def test_after_free_wins_high_random_loses(session, monkeypatch):
    await _make_user(session, balance=100, games_played=2)
    monkeypatch.setattr("bot.services.games.random.random", lambda: 0.99)
    result = await play_rps(session, 1, 10, "rock")
    assert result["outcome"] == "lose"
    assert result["bot_move"] == "paper"
    user = await session.get(User, 1)
    assert user.balance_tenths == 90


@pytest.mark.asyncio
async def test_after_free_wins_low_random_wins(session, monkeypatch):
    await _make_user(session, balance=100, games_played=2)
    monkeypatch.setattr("bot.services.games.random.random", lambda: 0.0)
    result = await play_rps(session, 1, 10, "rock")
    assert result["outcome"] == "win"
    assert result["bot_move"] == "scissors"
    user = await session.get(User, 1)
    assert user.balance_tenths == 110


@pytest.mark.asyncio
async def test_bet_below_minimum_raises(session):
    await _make_user(session, balance=100)
    with pytest.raises(GameError):
        await play_rps(session, 1, 4, "rock")


@pytest.mark.asyncio
async def test_bet_above_balance_raises(session):
    await _make_user(session, balance=10)
    with pytest.raises(GameError):
        await play_rps(session, 1, 50, "rock")
