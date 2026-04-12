import time
from typing import Any

import httpx

from app.config import settings
from app.repositories.session_repository import SessionRepository


async def fetch_deck_cards(deck_id: str, token: str) -> list[dict]:
    """Fetch flashcards from deck-service via internal HTTP."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.deck_service_url}/decks/{deck_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
        resp.raise_for_status()
        deck = resp.json()
        return [
            {"id": c["id"], "term": c["term"], "definition": c["definition"]}
            for c in deck.get("flashcards", [])
        ]


def calculate_score(is_correct: bool, response_time_ms: float, time_limit_s: int) -> int:
    if not is_correct:
        return 0
    base = 1000
    max_bonus = 1000
    time_limit_ms = time_limit_s * 1000
    speed_ratio = max(0.0, 1.0 - response_time_ms / time_limit_ms)
    bonus = int(max_bonus * speed_ratio)
    return base + bonus


def build_leaderboard(players: dict) -> list[dict]:
    ranked = sorted(
        [
            {"display_name": p["display_name"], "score": p["score"]}
            for p in players.values()
        ],
        key=lambda x: x["score"],
        reverse=True,
    )
    for i, entry in enumerate(ranked):
        entry["rank"] = i + 1
    return ranked


async def process_answer(
    repo: SessionRepository,
    pin: str,
    user_id: str,
    answer: str,
) -> dict:
    """Record player answer, compute score, return result info."""
    room = await repo.get_room(pin)
    if not room or room["status"] != "in_progress":
        return {"error": "Session not active"}

    idx = room["current_question_index"]
    q_state = await repo.get_question_state(pin, idx)
    if q_state is None:
        return {"error": "Question state missing"}

    if user_id in q_state["answers"]:
        return {"error": "Already answered"}

    card = room["cards"][idx]
    correct_def = card["definition"].strip().lower()
    submitted = answer.strip().lower()
    is_correct = submitted == correct_def

    response_time_ms = (time.time() - q_state["started_at"]) * 1000
    score_delta = calculate_score(is_correct, response_time_ms, room["question_time_limit"])

    q_state["answers"][user_id] = {
        "answer": answer,
        "is_correct": is_correct,
        "response_time_ms": response_time_ms,
    }
    await repo.save_question_state(pin, idx, q_state)

    # Update player score
    if user_id in room["players"]:
        room["players"][user_id]["score"] = room["players"][user_id].get("score", 0) + score_delta
        room["players"][user_id]["answered_current"] = True
    await repo.save_room(room)

    answered_count = len(q_state["answers"])
    total = len(room["players"])
    return {
        "answered_count": answered_count,
        "total": total,
        "all_answered": answered_count >= total,
    }


async def end_question(repo: SessionRepository, pin: str) -> dict:
    """Compute final question results and leaderboard."""
    room = await repo.get_room(pin)
    idx = room["current_question_index"]
    card = room["cards"][idx]
    leaderboard = build_leaderboard(room["players"])
    return {
        "correct_answer": card["definition"],
        "leaderboard": leaderboard,
    }
