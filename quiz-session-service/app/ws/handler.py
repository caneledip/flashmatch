import json
import uuid

from fastapi import WebSocket, WebSocketDisconnect

from app.repositories.session_repository import SessionRepository
from app.services.session_service import process_answer, end_question, build_leaderboard
from app.ws.connection_manager import manager


async def handle_websocket(ws: WebSocket, repo: SessionRepository, token_user=None):
    """
    Main WebSocket handler. The client sends a join_session message first,
    then subsequent game events.
    """
    await ws.accept()
    pin: str | None = None
    user_id: str | None = None

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await manager.send_personal(ws, {"type": "error", "message": "Invalid JSON"})
                continue

            event = msg.get("type")

            # ── join_session ──────────────────────────────────────────────────
            if event == "join_session":
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

                # Use provided user_id from auth token if available, else random
                user_id = str(token_user.id) if token_user else str(uuid.uuid4())

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
                if pin is None or user_id is None:
                    await manager.send_personal(ws, {"type": "error", "message": "Not in a session"})
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
                        "scores": {
                            uid: p["score"] for uid, p in room["players"].items()
                        },
                    })
                    await manager.broadcast(pin, {
                        "type": "leaderboard",
                        "rankings": q_result["leaderboard"],
                    })

            # ── next_question (host only) ──────────────────────────────────────
            elif event == "next_question":
                if pin is None:
                    continue
                room = await repo.get_room(pin)
                if not room:
                    continue

                # Verify host
                if user_id and str(room.get("host_id")) != user_id:
                    # Allow admin-role clients too; here we just check host_id
                    await manager.send_personal(ws, {"type": "error", "message": "Only the host can advance questions"})
                    continue

                next_idx = room["current_question_index"] + 1
                if next_idx >= len(room["cards"]):
                    # No more questions — session finished
                    room["status"] = "finished"
                    await repo.save_room(room)
                    final = build_leaderboard(room["players"])
                    await manager.broadcast(pin, {
                        "type": "session_finished",
                        "final_rankings": final,
                    })
                else:
                    room["current_question_index"] = next_idx
                    # Reset answered_current for all players
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
                if pin is None:
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
                # Close all connections
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
        if pin and user_id:
            manager.remove(pin, ws)
    except Exception:
        if pin:
            manager.remove(pin, ws)
