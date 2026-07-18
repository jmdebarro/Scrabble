import json
import os
import tempfile
from pathlib import Path


temporary_directory = tempfile.TemporaryDirectory()
os.environ["SCRABBLE_DB_PATH"] = str(Path(temporary_directory.name) / "scrabble-test.db")
os.environ["SCRABBLE_SOLVER_POOL_SIZE"] = "1"
os.environ["SCRABBLE_SOLVER_TIMEOUT"] = "20"

from fastapi.testclient import TestClient

from game_store import GameStore
from rules import create_board, evaluate_move
from server import app, solver_pool, store


def create_human_game(client: TestClient):
    created = client.post("/api/games", json={"mode": "human", "playerName": "Alice"})
    assert created.status_code == 201, created.text
    player_1 = created.json()
    joined = client.post(
        f"/api/games/{player_1['snapshot']['joinCode']}/join",
        json={"playerName": "Bob"},
    )
    assert joined.status_code == 200, joined.text
    return player_1, joined.json()


def run_tests():
    opening = evaluate_move(
        create_board(),
        [
            {"r": 7, "c": 7, "letter": "A", "isBlank": False},
            {"r": 7, "c": 8, "letter": "T", "isBlank": False},
        ],
    )
    assert opening.words == ["AT"] and opening.score == 4
    assert opening.modifiers == [{"r": 7, "c": 7, "multiplier": "double_word"}]

    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"status": "ok"}

        player_1, player_2 = create_human_game(client)
        game = player_2["snapshot"]
        game_id = game["gameId"]
        token_1, token_2 = player_1["token"], player_2["token"]
        assert game["status"] == "active" and game["version"] == 1
        assert "bag" not in game and len(game["rack"]) == 7

        with client.websocket_connect(f"/api/games/{game_id}/events?token={token_1}") as websocket:
            initial_event = websocket.receive_json()
            assert initial_event["type"] == "game_state"
            passed = client.post(
                f"/api/games/{game_id}/actions",
                headers={"X-Player-Token": token_1},
                json={"type": "pass", "expectedVersion": 1},
            )
            assert passed.status_code == 200, passed.text
            event = websocket.receive_json()
            assert event["snapshot"]["version"] == 2

        after_pass = passed.json()
        exchange_tile = player_2["snapshot"]["rack"][0]
        exchanged = client.post(
            f"/api/games/{game_id}/actions",
            headers={"X-Player-Token": token_2},
            json={"type": "exchange", "expectedVersion": after_pass["version"], "tiles": [exchange_tile]},
        )
        assert exchanged.status_code == 200, exchanged.text
        assert exchanged.json()["activePlayer"] == 0

        stale = client.post(
            f"/api/games/{game_id}/actions",
            headers={"X-Player-Token": token_1},
            json={"type": "pass", "expectedVersion": 1},
        )
        assert stale.status_code == 409

        resigned = client.post(
            f"/api/games/{game_id}/actions",
            headers={"X-Player-Token": token_1},
            json={"type": "resign", "expectedVersion": exchanged.json()["version"]},
        )
        assert resigned.status_code == 200, resigned.text
        assert resigned.json()["status"] == "finished" and resigned.json()["winner"] == 1

        play_owner, play_joiner = create_human_game(client)
        play_id = play_joiner["snapshot"]["gameId"]
        with store.transaction() as db:
            db.execute(
                "UPDATE games SET rack_1_json = ?, rack_2_json = ?, bag_json = ? WHERE id = ?",
                (json.dumps(["A", "T"]), json.dumps(["E"]), json.dumps(["Z"]), play_id),
            )
        played = client.post(
            f"/api/games/{play_id}/actions",
            headers={"X-Player-Token": play_owner["token"]},
            json={
                "type": "play",
                "expectedVersion": 1,
                "placements": [
                    {"r": 7, "c": 7, "letter": "A", "isBlank": False},
                    {"r": 7, "c": 8, "letter": "T", "isBlank": False},
                ],
            },
        )
        assert played.status_code == 200, played.text
        assert played.json()["moves"][0]["words"] == ["AT"]
        assert played.json()["moves"][0]["modifiers"] == [{"r": 7, "c": 7, "multiplier": "double_word"}]
        assert played.json()["status"] == "active"
        assert played.json()["finalTurnsRemaining"] == 2
        assert played.json()["activePlayer"] == 1

        player_2_final = client.post(
            f"/api/games/{play_id}/actions",
            headers={"X-Player-Token": play_joiner["token"]},
            json={"type": "pass", "expectedVersion": played.json()["version"]},
        )
        assert player_2_final.status_code == 200, player_2_final.text
        assert player_2_final.json()["status"] == "active"
        assert player_2_final.json()["finalTurnsRemaining"] == 1
        assert player_2_final.json()["activePlayer"] == 0

        player_1_final = client.post(
            f"/api/games/{play_id}/actions",
            headers={"X-Player-Token": play_owner["token"]},
            json={"type": "pass", "expectedVersion": player_2_final.json()["version"]},
        )
        assert player_1_final.status_code == 200, player_1_final.text
        assert player_1_final.json()["status"] == "finished"
        assert player_1_final.json()["finalTurnsRemaining"] == 0
        assert player_1_final.json()["finishReason"] == "final turns completed after bag emptied"

        persisted_store = GameStore(os.environ["SCRABBLE_DB_PATH"])
        persisted = persisted_store.get_snapshot(play_id, play_owner["token"])
        assert persisted["board"][7][7]["letter"] == "A"

        pass_owner, pass_joiner = create_human_game(client)
        pass_id = pass_joiner["snapshot"]["gameId"]
        pass_tokens = [pass_owner["token"], pass_joiner["token"]]
        pass_snapshot = pass_joiner["snapshot"]
        for turn in range(6):
            passed_turn = client.post(
                f"/api/games/{pass_id}/actions",
                headers={"X-Player-Token": pass_tokens[turn % 2]},
                json={"type": "pass", "expectedVersion": pass_snapshot["version"]},
            )
            assert passed_turn.status_code == 200, passed_turn.text
            pass_snapshot = passed_turn.json()
        assert pass_snapshot["status"] == "finished"
        assert pass_snapshot["finishReason"] == "six consecutive scoreless turns"

        bot_game = client.post("/api/games", json={"mode": "bot", "playerName": "Human"}).json()
        bot_id = bot_game["snapshot"]["gameId"]
        bot_turn = client.post(
            f"/api/games/{bot_id}/actions",
            headers={"X-Player-Token": bot_game["token"]},
            json={"type": "pass", "expectedVersion": 0},
        )
        assert bot_turn.status_code == 200, bot_turn.text
        bot_snapshot = bot_turn.json()
        assert len(bot_snapshot["moves"]) == 2
        assert bot_snapshot["activePlayer"] == 0 or bot_snapshot["status"] == "finished"
        assert bot_snapshot["moves"][0]["player"] == "GADDAG Bot"

    solver_pool.close()
    temporary_directory.cleanup()
    print("All authoritative game, SQLite, WebSocket, action, persistence, and bot tests passed.")


if __name__ == "__main__":
    run_tests()
