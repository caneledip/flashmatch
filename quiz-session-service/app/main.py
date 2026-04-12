from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated

from app.config import settings
from app.dependencies import get_current_user, require_host, TokenUser
from app.repositories.session_repository import SessionRepository
from app.schemas.session import CreateSessionRequest, CreateSessionResponse, SessionStatusResponse
from app.services.session_service import fetch_deck_cards
from app.ws.handler import handle_websocket
from app.ws.connection_manager import manager

redis_client: aioredis.Redis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    yield
    await redis_client.aclose()


app = FastAPI(title="FlashMatch Quiz Session Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_repo() -> SessionRepository:
    return SessionRepository(redis_client)


# ── REST endpoints ────────────────────────────────────────────────────────────

@app.post("/sessions/", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: CreateSessionRequest,
    current_user: Annotated[TokenUser, Depends(require_host)],
    repo: SessionRepository = Depends(get_repo),
):
    """Host creates a new quiz session. Fetches cards from deck-service and stores in Redis."""
    # We need a JWT to call deck-service; re-use the raw token via a workaround.
    # The token was already validated — re-encode a minimal one for internal call.
    from app.config import settings as cfg
    from jose import jwt
    from datetime import datetime, timedelta, timezone
    token_payload = {
        "sub": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role,
        "display_name": current_user.display_name,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    internal_token = jwt.encode(token_payload, cfg.jwt_secret, algorithm=cfg.jwt_algorithm)

    try:
        cards = await fetch_deck_cards(str(body.deck_id), internal_token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch deck from deck-service")

    if not cards:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Deck has no flashcards")

    pin = await repo.generate_pin()
    await repo.create_room(
        pin=pin,
        host_id=str(current_user.id),
        deck_id=str(body.deck_id),
        cards=cards,
        question_time_limit=body.question_time_limit,
    )
    return CreateSessionResponse(pin=pin, deck_id=body.deck_id, question_time_limit=body.question_time_limit)


@app.get("/sessions/{pin}", response_model=SessionStatusResponse)
async def get_session(pin: str, repo: SessionRepository = Depends(get_repo)):
    room = await repo.get_room(pin)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return SessionStatusResponse(
        pin=room["pin"],
        status=room["status"],
        player_count=len(room.get("players", {})),
        current_question_index=room["current_question_index"],
    )


@app.post("/sessions/{pin}/start", status_code=status.HTTP_200_OK)
async def start_session(
    pin: str,
    current_user: Annotated[TokenUser, Depends(require_host)],
    repo: SessionRepository = Depends(get_repo),
):
    """Host starts the quiz — broadcasts first question to all WebSocket clients."""
    room = await repo.get_room(pin)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if str(room["host_id"]) != str(current_user.id) and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your session")
    if room["status"] != "waiting":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session already started")

    room["status"] = "in_progress"
    await repo.save_room(room)
    await repo.create_question_state(pin, 0)

    card = room["cards"][0]
    await manager.broadcast(pin, {
        "type": "question_start",
        "index": 0,
        "term": card["term"],
        "time_limit": room["question_time_limit"],
    })
    return {"status": "started"}


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@app.websocket("/ws/session")
async def websocket_session(ws: WebSocket, repo: SessionRepository = Depends(get_repo)):
    """
    Single WebSocket endpoint for both host and players.
    Host authenticates via host_connect { token }.
    Players join via join_session { pin, display_name } — no account required.
    """
    await handle_websocket(ws, repo)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "quiz-session-service"}
