from __future__ import annotations

import random

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import User

MOVES = ("rock", "scissors", "paper")
BEATS = {"rock": "scissors", "scissors": "paper", "paper": "rock"}  # key beats value
LOSES_TO = {value: key for key, value in BEATS.items()}
WIN_CHANCE_AFTER_FREE = 0.30
FREE_WINS = 2
MIN_BET_TENTHS = 5


class GameError(Exception):
    pass


def _bot_move_for_outcome(user_move: str, outcome: str) -> str:
    if outcome == "win":
        return BEATS[user_move]
    if outcome == "lose":
        return LOSES_TO[user_move]
    return user_move


async def play_rps(session: AsyncSession, user_id: int, bet_tenths: int, user_move: str) -> dict:
    if user_move not in MOVES:
        raise GameError("Некорректный ход.")
    if bet_tenths < MIN_BET_TENTHS:
        raise GameError("Минимальная ставка — 0.5 ★.")
    user = await session.get(User, user_id)
    if user is None:
        raise GameError("Профиль не найден.")
    if user.balance_tenths < bet_tenths:
        raise GameError("Недостаточно звёзд.")

    if user.games_played < FREE_WINS:
        outcome = "win"
    else:
        outcome = "win" if random.random() < WIN_CHANCE_AFTER_FREE else "lose"

    bot_move = _bot_move_for_outcome(user_move, outcome)
    if outcome == "win":
        user.balance_tenths += bet_tenths
        user.total_earned_tenths += bet_tenths
    else:
        user.balance_tenths -= bet_tenths
    user.games_played += 1
    await session.commit()
    return {"outcome": outcome, "bot_move": bot_move, "user_move": user_move, "bet": bet_tenths}
