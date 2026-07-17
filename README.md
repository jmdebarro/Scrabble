# Oh My Pi Scrabble

A server-authoritative Scrabble game for private two-player matches or games against a C++ GADDAG bot.

## Architecture

- React + TypeScript frontend
- FastAPI HTTP and WebSocket server
- SQLite persistence at `backend/data/scrabble.db`
- Persistent pool of native C++ GADDAG solver processes

The server owns the board, bag, racks, scores, turns, validation, and game completion. Browser validation is only presentational.

## Local setup

From the repository root:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
npm --prefix frontend install
c++ -std=c++17 -O3 backend/src/main.cpp -o backend/src/gaddag_solver
```

The solver binary is generated locally and intentionally excluded from Git. Recompile it with the final command after changing `main.cpp` or when setting up a new machine.

## Run locally

Open two terminals from the repository root.

Terminal 1 — API, WebSockets, SQLite, and bot workers:

```bash
backend/.venv/bin/python backend/src/server.py
```

Terminal 2 — React development server:

```bash
npm --prefix frontend run dev
```

Then open [http://localhost:5173](http://localhost:5173).

- **Create Friend Game** displays an invite URL and short join code. Open the URL in a private window or second browser to join as the other player.
- **Play the Bot** starts a game whose second player is the GADDAG solver.
- Refreshing or reopening the same invite URL reconnects using the guest token stored in that browser.

The Vite development server proxies `/api` HTTP and WebSocket traffic to `127.0.0.1:5001`.

## Tests

Run the complete backend integration test:

```bash
PYTHONPATH=backend/src backend/.venv/bin/python backend/src/test_api.py
```

It covers rules, SQLite persistence, private game joining, WebSocket state delivery, optimistic version checks, play, exchange, pass, resignation, endgame, and a real bot turn.

Check and build the frontend:

```bash
frontend/node_modules/.bin/tsc -p frontend/tsconfig.json --noEmit
npm --prefix frontend run build
```

## Configuration

Environment variables:

- `PORT` — API port, default `5001`
- `SCRABBLE_DB_PATH` — SQLite file path, default `backend/data/scrabble.db`
- `SCRABBLE_ALLOWED_ORIGINS` — comma-separated CORS origins
- `SCRABBLE_SOLVER_POOL_SIZE` — native bot worker count, default `2`
- `SCRABBLE_SOLVER_TIMEOUT` — seconds allowed per bot request, default `15`

Deleting the SQLite database resets all local games. The `backend/data/` directory is intentionally ignored by Git.
