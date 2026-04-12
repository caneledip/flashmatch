import asyncio
import json
from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    """Manages active WebSocket connections keyed by room PIN."""

    def __init__(self):
        # pin -> set of WebSocket
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)

    def add(self, pin: str, ws: WebSocket):
        self._rooms[pin].add(ws)

    def remove(self, pin: str, ws: WebSocket):
        self._rooms[pin].discard(ws)
        if not self._rooms[pin]:
            del self._rooms[pin]

    async def broadcast(self, pin: str, message: dict):
        payload = json.dumps(message)
        dead = set()
        for ws in list(self._rooms.get(pin, [])):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.remove(pin, ws)

    async def send_personal(self, ws: WebSocket, message: dict):
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            pass

    def connection_count(self, pin: str) -> int:
        return len(self._rooms.get(pin, []))


manager = ConnectionManager()
