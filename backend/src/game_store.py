from __future__ import annotations

import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from rules import (
    BOARD_MULTIPLIERS,
    RuleError,
    apply_move,
    create_bag,
    create_board,
    draw_tiles,
    evaluate_move,
    rack_value,
    remove_exchange_tiles,
    remove_rack_tiles,
)


class GameError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class GameStore:
    def __init__(self, database_path: str | Path | None = None):
        default_path = Path(__file__).resolve().parent.parent / "data" / "scrabble.db"
        self.path = Path(database_path or os.environ.get("SCRABBLE_DB_PATH", default_path))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS games (
                    id TEXT PRIMARY KEY,
                    join_code TEXT NOT NULL UNIQUE,
                    mode TEXT NOT NULL CHECK (mode IN ('human', 'bot')),
                    status TEXT NOT NULL CHECK (status IN ('waiting', 'active', 'finished')),
                    board_json TEXT NOT NULL,
                    bag_json TEXT NOT NULL,
                    rack_1_json TEXT NOT NULL,
                    rack_2_json TEXT NOT NULL,
                    player_1_name TEXT NOT NULL,
                    player_1_token TEXT NOT NULL,
                    player_2_name TEXT,
                    player_2_token TEXT,
                    score_1 INTEGER NOT NULL DEFAULT 0,
                    score_2 INTEGER NOT NULL DEFAULT 0,
                    active_player INTEGER NOT NULL DEFAULT 0,
                    consecutive_scoreless INTEGER NOT NULL DEFAULT 0,
                    final_turns_remaining INTEGER NOT NULL DEFAULT -1,
                    board_layout_version INTEGER NOT NULL DEFAULT 2,
                    version INTEGER NOT NULL DEFAULT 0,
                    winner INTEGER,
                    finish_reason TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS moves (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
                    turn_number INTEGER NOT NULL,
                    player_index INTEGER NOT NULL,
                    player_name TEXT NOT NULL,
                    action TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    score INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS moves_game_turn_idx ON moves(game_id, turn_number);
                """
            )
            game_columns = {column["name"] for column in db.execute("PRAGMA table_info(games)")}
            if "final_turns_remaining" not in game_columns:
                db.execute(
                    "ALTER TABLE games ADD COLUMN final_turns_remaining INTEGER NOT NULL DEFAULT -1"
                )
            if "board_layout_version" not in game_columns:
                db.execute(
                    "ALTER TABLE games ADD COLUMN board_layout_version INTEGER NOT NULL DEFAULT 1"
                )
            legacy_games = db.execute(
                "SELECT id, board_json FROM games WHERE board_layout_version < 2"
            ).fetchall()
            for game in legacy_games:
                board = self._load(game["board_json"])
                for r, row in enumerate(board):
                    for c, square in enumerate(row):
                        square["multiplier"] = BOARD_MULTIPLIERS[r][c]
                db.execute(
                    """
                    UPDATE games
                    SET board_json = ?, board_layout_version = 2,
                        version = version + 1, updated_at = ?
                    WHERE id = ?
                    """,
                    (self._dump(board), utc_now(), game["id"]),
                )

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        db = self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def create_game(self, mode: str, player_name: str) -> dict[str, Any]:
        if mode not in {"human", "bot"}:
            raise GameError("Mode must be human or bot.")
        name = self._clean_name(player_name)
        game_id = str(uuid4())
        join_code = secrets.token_hex(4).upper()
        player_token = secrets.token_urlsafe(32)
        bot_token = f"bot:{secrets.token_urlsafe(24)}" if mode == "bot" else None
        bag = create_bag()
        secrets.SystemRandom().shuffle(bag)
        rack_1: list[str] = []
        rack_2: list[str] = []
        draw_tiles(bag, rack_1)
        status = "waiting"
        player_2_name = None
        if mode == "bot":
            draw_tiles(bag, rack_2)
            player_2_name = "GADDAG Bot"
            status = "active"
        now = utc_now()
        with self.transaction() as db:
            db.execute(
                """
                INSERT INTO games (
                    id, join_code, mode, status, board_json, bag_json,
                    rack_1_json, rack_2_json, player_1_name, player_1_token,
                    player_2_name, player_2_token, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    game_id, join_code, mode, status, self._dump(create_board()), self._dump(bag),
                    self._dump(rack_1), self._dump(rack_2), name, player_token,
                    player_2_name, bot_token, now, now,
                ),
            )
        return {"token": player_token, "snapshot": self.get_snapshot(game_id, player_token)}

    def join_game(self, game_reference: str, player_name: str) -> dict[str, Any]:
        name = self._clean_name(player_name)
        token = secrets.token_urlsafe(32)
        with self.transaction() as db:
            row = self._find_game(db, game_reference)
            if row["mode"] != "human" or row["status"] != "waiting":
                raise GameError("This game is not available to join.", 409)
            bag = self._load(row["bag_json"])
            rack_2: list[str] = []
            draw_tiles(bag, rack_2)
            db.execute(
                """
                UPDATE games
                SET player_2_name = ?, player_2_token = ?, rack_2_json = ?, bag_json = ?,
                    status = 'active', version = version + 1, updated_at = ?
                WHERE id = ?
                """,
                (name, token, self._dump(rack_2), self._dump(bag), utc_now(), row["id"]),
            )
            game_id = row["id"]
        return {"token": token, "snapshot": self.get_snapshot(game_id, token)}

    def get_snapshot(self, game_reference: str, token: str) -> dict[str, Any]:
        with self.connect() as db:
            row = self._find_game(db, game_reference)
            player_index = self._player_index(row, token)
            move_rows = db.execute(
                "SELECT * FROM moves WHERE game_id = ? ORDER BY turn_number DESC LIMIT 100",
                (row["id"],),
            ).fetchall()
            return self._snapshot(row, player_index, move_rows)

    def perform_action(
        self,
        game_reference: str,
        token: str,
        expected_version: int,
        action: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = payload or {}
        with self.transaction() as db:
            row = self._find_game(db, game_reference)
            player_index = self._player_index(row, token)
            if row["status"] != "active":
                raise GameError("The game is not active.", 409)
            if expected_version != row["version"]:
                raise GameError("Game state changed; refresh and try again.", 409)
            if action != "resign" and player_index != row["active_player"]:
                raise GameError("It is not your turn.", 409)

            state = self._mutable_state(row)
            score_delta = 0
            move_payload: dict[str, Any] = {}
            scoreless = False

            try:
                if action == "play":
                    evaluation = evaluate_move(state["board"], payload.get("placements", []))
                    remove_rack_tiles(state["racks"][player_index], evaluation.placements)
                    apply_move(state["board"], evaluation.placements)
                    draw_tiles(state["bag"], state["racks"][player_index])
                    score_delta = evaluation.score
                    state["scores"][player_index] += score_delta
                    state["consecutive"] = 0 if score_delta > 0 else state["consecutive"] + 1
                    scoreless = score_delta == 0
                    move_payload = {
                        "placements": evaluation.placements,
                        "words": evaluation.words,
                        "modifiers": evaluation.modifiers,
                    }
                elif action == "exchange":
                    tiles = payload.get("tiles", [])
                    if not isinstance(tiles, list) or not 1 <= len(tiles) <= 7:
                        raise RuleError("Select between one and seven tiles to exchange.")
                    if len(state["bag"]) < 7:
                        raise RuleError("At least seven tiles must remain in the bag to exchange.")
                    returned = remove_exchange_tiles(state["racks"][player_index], tiles)
                    for _ in returned:
                        state["racks"][player_index].append(state["bag"].pop())
                    state["bag"].extend(returned)
                    secrets.SystemRandom().shuffle(state["bag"])
                    state["consecutive"] += 1
                    scoreless = True
                    move_payload = {"count": len(returned)}
                elif action == "pass":
                    state["consecutive"] += 1
                    scoreless = True
                elif action == "resign":
                    state["status"] = "finished"
                    state["winner"] = 1 - player_index
                    state["finish_reason"] = "resignation"
                else:
                    raise GameError("Unknown game action.")
            except RuleError as exc:
                raise GameError(str(exc)) from exc

            if state["status"] == "active" and state["final_turns"] < 0 and not state["bag"]:
                state["final_turns"] = 2
            elif state["status"] == "active" and state["final_turns"] > 0:
                state["final_turns"] -= 1
                if state["final_turns"] == 0:
                    self._finish_final_round(state)

            if (
                state["status"] == "active"
                and state["final_turns"] < 0
                and scoreless
                and state["consecutive"] >= 6
            ):
                self._finish_scoreless(state)
            if state["status"] == "active":
                state["active"] = 1 - player_index

            next_version = row["version"] + 1
            turn_number = db.execute(
                "SELECT COALESCE(MAX(turn_number), 0) + 1 FROM moves WHERE game_id = ?",
                (row["id"],),
            ).fetchone()[0]
            player_name = row[f"player_{player_index + 1}_name"]
            db.execute(
                """
                INSERT INTO moves (game_id, turn_number, player_index, player_name, action, payload_json, score, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (row["id"], turn_number, player_index, player_name, action, self._dump(move_payload), score_delta, utc_now()),
            )
            db.execute(
                """
                UPDATE games SET board_json = ?, bag_json = ?, rack_1_json = ?, rack_2_json = ?,
                    score_1 = ?, score_2 = ?, active_player = ?, consecutive_scoreless = ?,
                    final_turns_remaining = ?,
                    status = ?, winner = ?, finish_reason = ?, version = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    self._dump(state["board"]), self._dump(state["bag"]),
                    self._dump(state["racks"][0]), self._dump(state["racks"][1]),
                    state["scores"][0], state["scores"][1], state["active"], state["consecutive"],
                    state["final_turns"],
                    state["status"], state["winner"], state["finish_reason"], next_version, utc_now(), row["id"],
                ),
            )
            game_id = row["id"]
        return self.get_snapshot(game_id, token)

    def get_bot_turn(self, game_reference: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = self._find_game(db, game_reference)
            if row["mode"] != "bot" or row["status"] != "active" or row["active_player"] != 1:
                return None
            opponent_rack = self._load(row["rack_1_json"])
            unseen = self._load(row["bag_json"]) + opponent_rack
            return {
                "gameId": row["id"],
                "version": row["version"],
                "token": row["player_2_token"],
                "board": self._load(row["board_json"]),
                "rack": self._load(row["rack_2_json"]),
                "bag": unseen,
            }

    def _snapshot(self, row: sqlite3.Row, player_index: int, moves: list[sqlite3.Row]) -> dict[str, Any]:
        players = [
            {"name": row["player_1_name"], "score": row["score_1"], "tileCount": len(self._load(row["rack_1_json"]))},
            {
                "name": row["player_2_name"] or "Waiting for player",
                "score": row["score_2"],
                "tileCount": len(self._load(row["rack_2_json"])),
                "isBot": row["mode"] == "bot",
            },
        ]
        history = []
        for move in moves:
            details = self._load(move["payload_json"])
            history.append(
                {
                    "turn": move["turn_number"], "player": move["player_name"], "action": move["action"],
                    "score": move["score"], "words": details.get("words", []),
                    "modifiers": details.get("modifiers", []), "details": details,
                }
            )
        return {
            "gameId": row["id"], "joinCode": row["join_code"], "mode": row["mode"],
            "status": row["status"], "version": row["version"], "board": self._load(row["board_json"]),
            "bagCount": len(self._load(row["bag_json"])), "rack": self._load(row[f"rack_{player_index + 1}_json"]),
            "you": player_index, "activePlayer": row["active_player"], "players": players,
            "consecutiveScoreless": row["consecutive_scoreless"],
            "finalTurnsRemaining": max(row["final_turns_remaining"], 0), "moves": history,
            "winner": row["winner"], "finishReason": row["finish_reason"],
            "updatedAt": row["updated_at"],
        }

    def _mutable_state(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "board": self._load(row["board_json"]), "bag": self._load(row["bag_json"]),
            "racks": [self._load(row["rack_1_json"]), self._load(row["rack_2_json"])],
            "scores": [row["score_1"], row["score_2"]], "active": row["active_player"],
            "consecutive": row["consecutive_scoreless"], "status": row["status"],
            "final_turns": row["final_turns_remaining"],
            "winner": row["winner"], "finish_reason": row["finish_reason"],
        }

    @classmethod
    def _finish_final_round(cls, state: dict[str, Any]) -> None:
        empty_racks = [index for index, rack in enumerate(state["racks"]) if not rack]
        if len(empty_racks) == 1:
            cls._finish_went_out(state, empty_racks[0])
        else:
            state["scores"][0] -= rack_value(state["racks"][0])
            state["scores"][1] -= rack_value(state["racks"][1])
            state["status"] = "finished"
            state["winner"] = 0 if state["scores"][0] > state["scores"][1] else 1 if state["scores"][1] > state["scores"][0] else None
        state["finish_reason"] = "final turns completed after bag emptied"

    @staticmethod
    def _finish_went_out(state: dict[str, Any], player_index: int) -> None:
        opponent = 1 - player_index
        remaining = rack_value(state["racks"][opponent])
        state["scores"][opponent] -= remaining
        state["scores"][player_index] += remaining
        state["status"] = "finished"
        state["winner"] = 0 if state["scores"][0] > state["scores"][1] else 1 if state["scores"][1] > state["scores"][0] else None
        state["finish_reason"] = "rack emptied"

    @staticmethod
    def _finish_scoreless(state: dict[str, Any]) -> None:
        state["scores"][0] -= rack_value(state["racks"][0])
        state["scores"][1] -= rack_value(state["racks"][1])
        state["status"] = "finished"
        state["winner"] = 0 if state["scores"][0] > state["scores"][1] else 1 if state["scores"][1] > state["scores"][0] else None
        state["finish_reason"] = "six consecutive scoreless turns"

    @staticmethod
    def _clean_name(name: str) -> str:
        cleaned = " ".join((name or "").strip().split())
        if not 1 <= len(cleaned) <= 30:
            raise GameError("Player name must be between 1 and 30 characters.")
        return cleaned

    @staticmethod
    def _player_index(row: sqlite3.Row, token: str) -> int:
        if token and secrets.compare_digest(token, row["player_1_token"]):
            return 0
        if token and row["player_2_token"] and secrets.compare_digest(token, row["player_2_token"]):
            return 1
        raise GameError("Player token is invalid for this game.", 403)

    @staticmethod
    def _find_game(db: sqlite3.Connection, reference: str) -> sqlite3.Row:
        row = db.execute(
            "SELECT * FROM games WHERE id = ? OR join_code = ?",
            (reference, reference.upper()),
        ).fetchone()
        if row is None:
            raise GameError("Game not found.", 404)
        return row

    @staticmethod
    def _dump(value: Any) -> str:
        return json.dumps(value, separators=(",", ":"))

    @staticmethod
    def _load(value: str) -> Any:
        return json.loads(value)
