import json
import uuid

from fastapi import WebSocket, WebSocketDisconnect
from jose import jwt, JWTError

from app.config import settings
from app.repositories.session_repository import SessionRepository
from app.services.session_service import process_answer, end_question, build_leaderboard
from app.ws.connection_manager import manager


async def handle_websocket(ws: WebSocket, repo: SessionRepository):
    """
    Main WebSocket handler for both host and players.

    First message must be one of:
      - host_connect   { type, pin, token }   — host authenticates via JWT
      - join_session   { type, pin, display_name }  — player joins by PIN
    """
    await ws.accept()
    pin: str | None = None
    user_id: str | None = None
    is_host: bool = False

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await manager.send_personal(ws, {"type": "error", "message": "Invalid JSON"})
                continue

            event = msg.get("type")

            # ── host_connect ──────────────────────────────────────────────────
            if event == "host_connect":
                token = msg.get("token", "")
                pin = msg.get("pin")

                # Validate JWT
                try:
                    payload = jwt.decode(
                        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
                    )
                    user_id = payload.get("sub")
                except JWTError:
                    await manager.send_personal(ws, {"type": "error", "message": "Invalid token"})
                    await ws.close()
                    return

                room = await repo.get_room(pin)
                if not room:
                    await manager.send_personal(ws, {"type": "error", "message": "Room not found"})
                    await ws.close()
                    return

                if str(room["host_id"]) != str(user_id) and payload.get("role") != "admin":
                    await manager.send_personal(ws, {"type": "error", "message": "Not the host of this session"})
                    await ws.close()
                    return

                is_host = True
                manager.add(pin, ws)
                await manager.send_personal(ws, {
                    "type": "host_connected",
                    "pin": pin,
                    "player_count": len(room.get("players", {})),
                })

            # ── join_session (players) ────────────────────────────────────────
            elif event == "join_session":
                pin = msg.get("pin")
                display_name = msg.get("display_name", "Player")

                room = await repo.get_room(pin)
                if not room:
                    await manager.send_personal(ws, {"type": "error", "message": "Room not found"})
                    await ws.close()
                    return

                if room["status"] != "waiting":
                    await manager.send_personal(ws, {"type": "error", "message": "Session already started"})
                    await ws.close()
                    return

                user_id = str(uuid.uuid4())

                room["players"][user_id] = {
                    "display_name": display_name,
                    "score": 0,
                    "answered_current": False,
                }
                await repo.save_room(room)
                manager.add(pin, ws)

                await manager.broadcast(pin, {
                    "type": "player_joined",
                    "display_name": display_name,
                    "player_count": len(room["players"]),
                })

            # ── submit_answer ─────────────────────────────────────────────────
            elif event == "submit_answer":
                if pin is None or user_id is None or is_host:
                    await manager.send_personal(ws, {"type": "error", "message": "Not in a session as a player"})
                    continue

                answer = msg.get("answer", "")
                result = await process_answer(repo, pin, user_id, answer)

                if "error" in result:
                    await manager.send_personal(ws, {"type": "error", "message": result["error"]})
                    continue

                await manager.broadcast(pin, {
                    "type": "answer_received",
                    "answered_count": result["answered_count"],
                    "total": result["total"],
                })

                # Auto-end question when everyone has answered
                if result["all_answered"]:
                    q_result = await end_question(repo, pin)
                    room = await repo.get_room(pin)
                    await manager.broadcast(pin, {
                        "type": "question_end",
                        "correct_answer": q_result["correct_answer"],
                        "scores": {uid: p["score"] for uid, p in room["players"].items()},
                    })
                    await manager.broadcast(pin, {
                        "type": "leaderboard",
                        "rankings": q_result["leaderboard"],
                    })

            # ── next_question (host only) ──────────────────────────────────────
            elif event == "next_question":
                if not is_host or pin is None:
                    await manager.send_personal(ws, {"type": "error", "message": "Only the host can advance questions"})
                    continue

                room = await repo.get_room(pin)
                if not room:
                    continue

                next_idx = room["current_question_index"] + 1
                if next_idx >= len(room["cards"]):
                    room["status"] = "finished"
                    await repo.save_room(room)
                    final = build_leaderboard(room["players"])
                    await manager.broadcast(pin, {
                        "type": "session_finished",
                        "final_rankings": final,
                    })
                else:
                    room["current_question_index"] = next_idx
                    for p in room["players"].values():
                        p["answered_current"] = False
                    room["status"] = "in_progress"
                    await repo.save_room(room)
                    await repo.create_question_state(pin, next_idx)

                    card = room["cards"][next_idx]
                    await manager.broadcast(pin, {
                        "type": "question_start",
                        "index": next_idx,
                        "term": card["term"],
                        "time_limit": room["question_time_limit"],
                    })

            # ── end_session (host only) ───────────────────────────────────────
            elif event == "end_session":
                if not is_host or pin is None:
                    await manager.send_personal(ws, {"type": "error", "message": "Only the host can end the session"})
                    continue

                room = await repo.get_room(pin)
                if not room:
                    continue

                final = build_leaderboard(room.get("players", {}))
                await manager.broadcast(pin, {
                    "type": "session_finished",
                    "final_rankings": final,
                })

                await repo.delete_room(pin)
                await repo.delete_question_states(pin, len(room.get("cards", [])))
                for conn_ws in list(manager._rooms.get(pin, [])):
                    try:
                        await conn_ws.close()
                    except Exception:
                        pass
                manager._rooms.pop(pin, None)
                return

            else:
                await manager.send_personal(ws, {"type": "error", "message": f"Unknown event: {event}"})

    except WebSocketDisconnect:
        if pin:
            manager.remove(pin, ws)
    except Exception:
        if pin:
            manager.remove(pin, ws)
