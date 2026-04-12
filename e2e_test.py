"""
E2E integration test — runs inside the Docker network.
Simulates: host creates deck → starts session → 2 players join + answer → leaderboard → end.
"""
import asyncio, json, uuid, subprocess, os
from datetime import datetime, timedelta, timezone
from jose import jwt
import httpx, websockets

HOST = os.environ.get("E2E_HOST", "http://nginx:80")
WS   = os.environ.get("E2E_WS",   "ws://nginx:80")
JWT_SECRET = "supersecretjwtkey_changethisinproduction"
JWT_ALG    = "HS256"

def make_token(user_id, role, display_name, email):
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "display_name": display_name,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def seed_host_user(host_id):
    # Seeding is done externally via docker exec on user-db before running this script.
    pass

async def run():
    host_id = os.environ.get("E2E_HOST_ID", str(uuid.uuid4()))
    seed_host_user(host_id)
    host_token = make_token(host_id, "host", "TestHost", "host@test.com")
    headers = {"Authorization": f"Bearer {host_token}"}

    async with httpx.AsyncClient(base_url=HOST, timeout=15) as client:
        # Create deck
        r = await client.post("/decks/", json={"title": "E2E Deck", "is_public": False}, headers=headers)
        assert r.status_code == 201, f"create deck: {r.text}"
        deck_id = r.json()["id"]
        print(f"✓ Deck created: {deck_id}")

        # Add 3 cards
        for i, (term, defn) in enumerate([
            ("Ephemeral", "Lasting for a very short time"),
            ("Ubiquitous", "Present everywhere"),
            ("Laconic", "Using very few words"),
        ]):
            r = await client.post(f"/decks/{deck_id}/cards",
                json={"term": term, "definition": defn, "position": i}, headers=headers)
            assert r.status_code == 201, f"add card: {r.text}"
        print("✓ 3 flashcards added")

        # Create session
        r = await client.post("/sessions/", json={"deck_id": deck_id, "question_time_limit": 20}, headers=headers)
        assert r.status_code == 201, f"create session: {r.text}"
        pin = r.json()["pin"]
        print(f"✓ Session created: PIN={pin}")

        async with (
            websockets.connect(f"{WS}/ws/session") as host_ws,
            websockets.connect(f"{WS}/ws/session") as p1_ws,
            websockets.connect(f"{WS}/ws/session") as p2_ws,
        ):
            # Host connects
            await host_ws.send(json.dumps({"type": "host_connect", "pin": pin, "token": host_token}))
            resp = json.loads(await host_ws.recv())
            assert resp["type"] == "host_connected", f"got {resp}"
            print("✓ Host WS connected")

            # Players join
            await p1_ws.send(json.dumps({"type": "join_session", "pin": pin, "display_name": "Alice"}))
            m = json.loads(await p1_ws.recv())
            _ = json.loads(await host_ws.recv())
            print(f"✓ Alice joined (count={m['player_count']})")

            await p2_ws.send(json.dumps({"type": "join_session", "pin": pin, "display_name": "Bob"}))
            m = json.loads(await p2_ws.recv())
            _ = json.loads(await host_ws.recv())
            _ = json.loads(await p1_ws.recv())
            print(f"✓ Bob joined (count={m['player_count']})")

            # Start session
            r = await client.post(f"/sessions/{pin}/start", headers=headers)
            assert r.status_code == 200, f"start: {r.text}"

            q = json.loads(await host_ws.recv())
            _ = json.loads(await p1_ws.recv())
            _ = json.loads(await p2_ws.recv())
            assert q["type"] == "question_start"
            print(f"✓ Q1 broadcast: '{q['term']}'")

            # Alice answers correctly (fast), Bob answers wrong
            await p1_ws.send(json.dumps({"type": "submit_answer", "pin": pin, "answer": "Lasting for a very short time"}))
            for ws_ in [host_ws, p1_ws, p2_ws]:
                _ = json.loads(await ws_.recv())  # answer_received (1/2)

            await p2_ws.send(json.dumps({"type": "submit_answer", "pin": pin, "answer": "Wrong"}))
            # Triggers answer_received + question_end + leaderboard
            collected = {}
            for ws_ in [host_ws, p1_ws, p2_ws]:
                for _ in range(3):
                    m = json.loads(await ws_.recv())
                    collected[m["type"]] = m

            assert "question_end" in collected
            assert "leaderboard" in collected
            print(f"✓ Q1 ended. Correct: '{collected['question_end']['correct_answer']}'")
            for e in collected["leaderboard"]["rankings"]:
                print(f"  #{e['rank']} {e['display_name']}: {e['score']} pts")

            # Host → next question
            await host_ws.send(json.dumps({"type": "next_question", "pin": pin}))
            q2 = json.loads(await host_ws.recv())
            _ = json.loads(await p1_ws.recv())
            _ = json.loads(await p2_ws.recv())
            assert q2["type"] == "question_start", f"got {q2}"
            print(f"✓ Q2 broadcast: '{q2['term']}'")

            # Host ends session
            await host_ws.send(json.dumps({"type": "end_session", "pin": pin}))
            fin = json.loads(await host_ws.recv())
            assert fin["type"] == "session_finished"
            print("✓ Session finished. Final:")
            for e in fin["final_rankings"]:
                print(f"  #{e['rank']} {e['display_name']}: {e['score']} pts")

        # Redis key should be gone
        r = await client.get(f"/sessions/{pin}")
        assert r.status_code == 404, f"expected 404, got {r.status_code}: {r.text}"
        print("✓ Redis session deleted (404 confirmed)")

    print("\n✅ All E2E checks passed!")

asyncio.run(run())
