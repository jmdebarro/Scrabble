from __future__ import annotations

import asyncio
import os
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any, Literal

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from game_store import GameError, GameStore
from solver_pool import SolverError, SolverPool


store = GameStore()
solver_pool = SolverPool()


class CreateGameRequest(BaseModel):
    mode: Literal["human", "bot"]
    playerName: str = Field(min_length=1, max_length=30)


class JoinGameRequest(BaseModel):
    playerName: str = Field(min_length=1, max_length=30)


class PlacementRequest(BaseModel):
    r: int = Field(ge=0, le=14)
    c: int = Field(ge=0, le=14)
    letter: str = Field(min_length=1, max_length=1)
    isBlank: bool = False


class GameActionRequest(BaseModel):
    type: Literal["play", "exchange", "pass", "resign"]
    expectedVersion: int = Field(ge=0)
    placements: list[PlacementRequest] = Field(default_factory=list)
    tiles: list[str] = Field(default_factory=list)


class BotMoveRequest(BaseModel):
    board: list[list[dict[str, Any]]]
    rack: list[str]
    bag: list[str]


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: dict[str, list[tuple[WebSocket, str]]] = defaultdict(list)
        self.lock = asyncio.Lock()

    async def connect(self, game_id: str, token: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self.lock:
            self.connections[game_id].append((websocket, token))

    async def disconnect(self, game_id: str, websocket: WebSocket) -> None:
        async with self.lock:
            self.connections[game_id] = [
                connection for connection in self.connections.get(game_id, []) if connection[0] is not websocket
            ]
            if not self.connections[game_id]:
                self.connections.pop(game_id, None)

    async def broadcast_state(self, game_id: str) -> None:
        async with self.lock:
            recipients = list(self.connections.get(game_id, []))
        stale: list[WebSocket] = []
        for websocket, token in recipients:
            try:
                snapshot = await asyncio.to_thread(store.get_snapshot, game_id, token)
                await websocket.send_json({"type": "game_state", "snapshot": snapshot})
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            await self.disconnect(game_id, websocket)


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    solver_pool.close()


app = FastAPI(title="Oh My Pi Scrabble API", version="1.0.0", lifespan=lifespan)
allowed_origins = os.environ.get(
    "SCRABBLE_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Player-Token"],
)


def require_token(token: str | None) -> str:
    if not token:
        raise HTTPException(status_code=401, detail="X-Player-Token header is required.")
    return token


def translate_game_error(exc: GameError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


async def run_bot_turn(game_id: str) -> None:
    turn = await asyncio.to_thread(store.get_bot_turn, game_id)
    if turn is None:
        return
    solver_payload = {"board": turn["board"], "rack": turn["rack"], "bag": turn["bag"]}
    try:
        result = await asyncio.to_thread(solver_pool.solve, solver_payload)
    except SolverError:
        result = {"success": False}

    if result.get("success") and result.get("tilesPlaced"):
        action = "play"
        payload = {"placements": result["tilesPlaced"]}
    else:
        action = "pass"
        payload = {}
    try:
        await asyncio.to_thread(
            store.perform_action,
            game_id,
            turn["token"],
            turn["version"],
            action,
            payload,
        )
    except GameError:
        if action == "play":
            await asyncio.to_thread(
                store.perform_action,
                game_id,
                turn["token"],
                turn["version"],
                "pass",
                {},
            )


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/games", status_code=201)
async def create_game(request: CreateGameRequest) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(store.create_game, request.mode, request.playerName)
    except GameError as exc:
        raise translate_game_error(exc) from exc


@app.post("/api/games/{game_reference}/join")
async def join_game(game_reference: str, request: JoinGameRequest) -> dict[str, Any]:
    try:
        result = await asyncio.to_thread(store.join_game, game_reference, request.playerName)
        await manager.broadcast_state(result["snapshot"]["gameId"])
        return result
    except GameError as exc:
        raise translate_game_error(exc) from exc


@app.get("/api/games/{game_reference}")
async def get_game(
    game_reference: str,
    x_player_token: str | None = Header(default=None),
) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(store.get_snapshot, game_reference, require_token(x_player_token))
    except GameError as exc:
        raise translate_game_error(exc) from exc


@app.post("/api/games/{game_reference}/actions")
async def perform_action(
    game_reference: str,
    request: GameActionRequest,
    x_player_token: str | None = Header(default=None),
) -> dict[str, Any]:
    token = require_token(x_player_token)
    payload = {
        "placements": [placement.model_dump() for placement in request.placements],
        "tiles": request.tiles,
    }
    try:
        snapshot = await asyncio.to_thread(
            store.perform_action,
            game_reference,
            token,
            request.expectedVersion,
            request.type,
            payload,
        )
        game_id = snapshot["gameId"]
        await manager.broadcast_state(game_id)
        await run_bot_turn(game_id)
        await manager.broadcast_state(game_id)
        return await asyncio.to_thread(store.get_snapshot, game_id, token)
    except GameError as exc:
        raise translate_game_error(exc) from exc


@app.post("/api/bot_move")
async def legacy_bot_move(request: BotMoveRequest) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(solver_pool.solve, request.model_dump())
    except SolverError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.websocket("/api/games/{game_reference}/events")
async def game_events(
    websocket: WebSocket,
    game_reference: str,
    token: str = Query(...),
) -> None:
    try:
        snapshot = await asyncio.to_thread(store.get_snapshot, game_reference, token)
    except GameError:
        await websocket.close(code=1008, reason="Invalid game or player token")
        return
    game_id = snapshot["gameId"]
    await manager.connect(game_id, token, websocket)
    await websocket.send_json({"type": "game_state", "snapshot": snapshot})
    try:
        while True:
            message = await websocket.receive_json()
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif message.get("type") == "resync":
                current = await asyncio.to_thread(store.get_snapshot, game_id, token)
                await websocket.send_json({"type": "game_state", "snapshot": current})
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(game_id, websocket)


def run_server(port: int = 5001) -> None:
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    run_server(int(os.environ.get("PORT", "5001")))
