import json
import random
import string
import time
from typing import Any

import redis.asyncio as aioredis

ROOM_TTL = 3 * 60 * 60      # 3 hours
QUESTION_TTL = 60 * 60      # 1 hour


def _room_key(pin: str) -> str:
    return f"room:{pin}"


def _question_key(pin: str, index: int) -> str:
    return f"room:{pin}:question:{index}"


class SessionRepository:
    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    # ── PIN generation ────────────────────────────────────────────────────────

    async def generate_pin(self) -> str:
        for _ in range(10):
            pin = "".join(random.choices(string.digits, k=6))
            exists = await self.redis.exists(_room_key(pin))
            if not exists:
                return pin
        raise RuntimeError("Could not generate a unique PIN after 10 attempts")

    # ── Room CRUD ─────────────────────────────────────────────────────────────

    async def create_room(self, pin: str, host_id: str, deck_id: str, cards: list[dict], question_time_limit: int = 20) -> dict:
        room = {
            "pin": pin,
            "host_id": host_id,
            "deck_id": deck_id,
            "status": "waiting",
            "current_question_index": 0,
            "question_time_limit": question_time_limit,
            "cards": cards,
            "players": {},
            "created_at": time.time(),
        }
        await self.redis.set(_room_key(pin), json.dumps(room), ex=ROOM_TTL)
        return room

    async def get_room(self, pin: str) -> dict | None:
        raw = await self.redis.get(_room_key(pin))
        if raw is None:
            return None
        return json.loads(raw)

    async def save_room(self, room: dict) -> None:
        pin = room["pin"]
        await self.redis.set(_room_key(pin), json.dumps(room), ex=ROOM_TTL)

    async def delete_room(self, pin: str) -> None:
        await self.redis.delete(_room_key(pin))

    # ── Question state ────────────────────────────────────────────────────────

    async def get_question_state(self, pin: str, index: int) -> dict | None:
        raw = await self.redis.get(_question_key(pin, index))
        if raw is None:
            return None
        return json.loads(raw)

    async def create_question_state(self, pin: str, index: int) -> dict:
        state = {"started_at": time.time(), "answers": {}}
        await self.redis.set(_question_key(pin, index), json.dumps(state), ex=QUESTION_TTL)
        return state

    async def save_question_state(self, pin: str, index: int, state: dict) -> None:
        await self.redis.set(_question_key(pin, index), json.dumps(state), ex=QUESTION_TTL)

    async def delete_question_states(self, pin: str, total_questions: int) -> None:
        keys = [_question_key(pin, i) for i in range(total_questions)]
        if keys:
            await self.redis.delete(*keys)
