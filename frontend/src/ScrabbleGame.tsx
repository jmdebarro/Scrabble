import { useEffect, useMemo, useRef, useState } from "react";
import Board from "./Board";
import Bench from "./Bench";
import { loadWords, validateAndScoreMove, type PlacedTile, type Square } from "./boardLogic";
import {
  createGame,
  GameSnapshot,
  joinGame,
  loadGame,
  sendAction,
  tokenStorageKey,
  websocketUrl,
} from "./gameApi";


interface PendingTile {
  r: number;
  c: number;
  letter: string;
  isBlank: boolean;
  originalIndex: number;
}


interface Feedback {
  text: string;
  type: "success" | "error" | "info";
}


export default function ScrabbleGame() {
  const initialReference = new URLSearchParams(window.location.search).get("game");
  const [gameReference, setGameReference] = useState<string | null>(initialReference);
  const [token, setToken] = useState<string | null>(() =>
    initialReference ? localStorage.getItem(tokenStorageKey(initialReference)) : null,
  );
  const [snapshot, setSnapshot] = useState<GameSnapshot | null>(null);
  const [rackView, setRackView] = useState<string[]>([]);
  const [pendingTiles, setPendingTiles] = useState<PendingTile[]>([]);
  const [selectedRackIndices, setSelectedRackIndices] = useState<number[]>([]);
  const [validWordSquares, setValidWordSquares] = useState<{ r: number; c: number }[]>([]);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [busy, setBusy] = useState(false);
  const [connected, setConnected] = useState(false);
  const lastVersion = useRef<number | null>(null);

  useEffect(() => {
    if (!gameReference || !token) return;
    let cancelled = false;
    setBusy(true);
    loadGame(gameReference, token)
      .then(game => {
        if (!cancelled) setSnapshot(game);
      })
      .catch(error => {
        if (!cancelled) {
          setFeedback({ text: error.message, type: "error" });
          localStorage.removeItem(tokenStorageKey(gameReference));
          setToken(null);
        }
      })
      .finally(() => !cancelled && setBusy(false));
    return () => {
      cancelled = true;
    };
  }, [gameReference, token]);

  useEffect(() => {
    if (!snapshot) return;
    if (lastVersion.current !== snapshot.version) {
      setRackView(snapshot.rack);
      setPendingTiles([]);
      setSelectedRackIndices([]);
      lastVersion.current = snapshot.version;
    }
  }, [snapshot]);

  useEffect(() => {
    if (!snapshot || !token) return;
    let socket: WebSocket | null = null;
    let reconnectTimer: number | null = null;
    let stopped = false;

    const connect = () => {
      socket = new WebSocket(websocketUrl(snapshot.gameId, token));
      socket.onopen = () => setConnected(true);
      socket.onmessage = event => {
        const message = JSON.parse(event.data);
        if (message.type === "game_state") setSnapshot(message.snapshot);
      };
      socket.onclose = () => {
        setConnected(false);
        if (!stopped) reconnectTimer = window.setTimeout(connect, 1500);
      };
      socket.onerror = () => socket?.close();
    };
    connect();
    return () => {
      stopped = true;
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [snapshot?.gameId, token]);

  const displayBoard = useMemo(() => {
    if (!snapshot) return [];
    const board = snapshot.board.map(row => row.map(square => ({ ...square })));
    for (const tile of pendingTiles) {
      board[tile.r][tile.c].letter = tile.letter;
      board[tile.r][tile.c].isBlank = tile.isBlank;
      board[tile.r][tile.c].isLocked = false;
    }
    return board;
  }, [snapshot, pendingTiles]);

  const rackDisplay = rackView.map((letter, index) =>
    pendingTiles.some(tile => tile.originalIndex === index) ? null : letter,
  );
  const isYourTurn = snapshot?.status === "active" && snapshot.activePlayer === snapshot.you;

  useEffect(() => {
    let cancelled = false;
    if (!snapshot || pendingTiles.length === 0) {
      setValidWordSquares([]);
      return;
    }

    const validatePendingWord = async () => {
      const placements: PlacedTile[] = pendingTiles.map(({ r, c, letter, isBlank }) => ({
        r,
        c,
        letter,
        isBlank,
      }));
      const result = validateAndScoreMove(displayBoard, placements);
      if (!result.success || !result.wordsFormed) {
        if (!cancelled) setValidWordSquares([]);
        return;
      }
      const dictionary = await loadWords();
      if (result.wordsFormed.some(word => !dictionary.has(word.word.toLowerCase()))) {
        if (!cancelled) setValidWordSquares([]);
        return;
      }
      const uniqueSquares = result.wordsFormed
        .flatMap(word => word.cells)
        .filter((cell, index, cells) => cells.findIndex(other => other.r === cell.r && other.c === cell.c) === index);
      if (!cancelled) setValidWordSquares(uniqueSquares);
    };

    void validatePendingWord();
    return () => {
      cancelled = true;
    };
  }, [displayBoard, pendingTiles, snapshot]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (!snapshot || !isYourTurn || busy) return;
      const activeTag = document.activeElement?.tagName;
      if (activeTag === "INPUT" || activeTag === "TEXTAREA" || activeTag === "SELECT") return;

      if (event.key >= "1" && event.key <= "7") {
        const index = Number(event.key) - 1;
        if (rackDisplay[index] !== null && rackDisplay[index] !== undefined) {
          event.preventDefault();
          setSelectedRackIndices(current =>
            current.includes(index) ? current.filter(value => value !== index) : [...current, index],
          );
        }
        return;
      }

      const isBlankKey = event.key === " " || event.key === "?";
      if (!isBlankKey && !/^[a-z]$/i.test(event.key)) return;
      const target = isBlankKey ? "?" : event.key.toUpperCase();
      const matchingIndices = rackDisplay
        .map((letter, index) => ({ letter, index }))
        .filter(item => item.letter === target)
        .map(item => item.index);
      if (matchingIndices.length === 0) return;

      event.preventDefault();
      setSelectedRackIndices(current => {
        const unselected = matchingIndices.find(index => !current.includes(index));
        if (unselected !== undefined) return [...current, unselected];
        const lastSelected = [...matchingIndices].reverse().find(index => current.includes(index));
        return lastSelected === undefined ? current : current.filter(index => index !== lastSelected);
      });
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [busy, isYourTurn, pendingTiles, rackView, selectedRackIndices, snapshot]);

  const establishSession = (sessionToken: string, game: GameSnapshot) => {
    localStorage.setItem(tokenStorageKey(game.gameId), sessionToken);
    localStorage.setItem(tokenStorageKey(game.joinCode), sessionToken);
    window.history.replaceState({}, "", `?game=${encodeURIComponent(game.gameId)}`);
    setGameReference(game.gameId);
    setToken(sessionToken);
    setSnapshot(game);
    setFeedback({ text: game.status === "waiting" ? "Game created. Share the invite link." : "Game ready.", type: "success" });
  };

  const runAction = async (type: "play" | "exchange" | "pass" | "resign", extra: Record<string, unknown> = {}) => {
    if (!snapshot || !token || busy) return;
    setBusy(true);
    try {
      const next = await sendAction(snapshot.gameId, token, {
        type,
        expectedVersion: snapshot.version,
        ...extra,
      });
      setSnapshot(next);
      setFeedback({
        text: type === "play" ? "Move accepted." : type === "exchange" ? "Tiles exchanged." : type === "pass" ? "Turn passed." : "Game resigned.",
        type: "success",
      });
    } catch (error) {
      setFeedback({ text: error instanceof Error ? error.message : "Action failed.", type: "error" });
      try {
        setSnapshot(await loadGame(snapshot.gameId, token));
      } catch {
        // Preserve the actionable error from the original request.
      }
    } finally {
      setBusy(false);
    }
  };

  const handleSquareClick = (r: number, c: number) => {
    if (!snapshot || !isYourTurn || busy) return;
    const existingPending = pendingTiles.find(tile => tile.r === r && tile.c === c);
    if (existingPending) {
      setPendingTiles(current => current.filter(tile => tile !== existingPending));
      return;
    }
    if (snapshot.board[r][c].letter !== null || selectedRackIndices.length === 0) return;
    const rackIndex = selectedRackIndices[0];
    const rackLetter = rackDisplay[rackIndex];
    if (!rackLetter) return;
    const isBlank = rackLetter === "?";
    let letter = rackLetter;
    if (isBlank) {
      const choice = window.prompt("Choose a letter for this blank (A-Z):")?.trim().toUpperCase();
      if (!choice || !/^[A-Z]$/.test(choice)) {
        setFeedback({ text: "A blank must represent one letter from A to Z.", type: "error" });
        return;
      }
      letter = choice;
    }
    setPendingTiles(current => [...current, { r, c, letter, isBlank, originalIndex: rackIndex }]);
    setSelectedRackIndices(current => current.filter(index => index !== rackIndex));
    setFeedback(null);
  };

  const submitMove = () => {
    if (!pendingTiles.length) {
      setFeedback({ text: "Place at least one tile first.", type: "error" });
      return;
    }
    void runAction("play", {
      placements: pendingTiles.map(({ r, c, letter, isBlank }) => ({ r, c, letter, isBlank })),
    });
  };

  const exchangeTiles = () => {
    const tiles = selectedRackIndices.map(index => rackDisplay[index]).filter((tile): tile is string => Boolean(tile));
    if (!tiles.length) {
      setFeedback({ text: "Select one or more rack tiles to exchange.", type: "error" });
      return;
    }
    void runAction("exchange", { tiles });
  };

  const shuffleRack = () => {
    if (pendingTiles.length) return;
    const shuffled = [...rackView];
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    setRackView(shuffled);
    setSelectedRackIndices([]);
  };

  if (!snapshot) {
    return (
      <Lobby
        gameReference={gameReference}
        busy={busy}
        feedback={feedback}
        onCreate={async (mode, name) => {
          setBusy(true);
          try {
            const session = await createGame(mode, name);
            establishSession(session.token, session.snapshot);
          } catch (error) {
            setFeedback({ text: error instanceof Error ? error.message : "Could not create game.", type: "error" });
          } finally {
            setBusy(false);
          }
        }}
        onJoin={async (reference, name) => {
          setBusy(true);
          try {
            const session = await joinGame(reference, name);
            establishSession(session.token, session.snapshot);
          } catch (error) {
            setFeedback({ text: error instanceof Error ? error.message : "Could not join game.", type: "error" });
          } finally {
            setBusy(false);
          }
        }}
      />
    );
  }

  const inviteUrl = `${window.location.origin}${window.location.pathname}?game=${encodeURIComponent(snapshot.gameId)}`;
  const statusMessage = snapshot.status === "waiting"
    ? "Waiting for another player"
    : snapshot.status === "finished"
      ? snapshot.winner === null
        ? `Game tied — ${snapshot.finishReason}`
        : `${snapshot.players[snapshot.winner].name} won — ${snapshot.finishReason}`
      : isYourTurn
        ? "Your turn"
        : `${snapshot.players[snapshot.activePlayer].name} is thinking`;

  return (
    <div className="game-container">
      <div className="game-layout">
        <div className="board-column">
          <div className="header-bar">
            <h1>Oh My Pi Scrabble</h1>
            <div className="game-status-line">
              <span className={`connection-dot ${connected ? "online" : "offline"}`} />
              {statusMessage}
            </div>
          </div>

          <Board
            board={displayBoard as Square[][]}
            onSquareClick={handleSquareClick}
            validWordSquares={validWordSquares}
          />

          <div className="rack-area">
            <div className="rack-label">Your Rack</div>
            <Bench
              bench={rackDisplay}
              selectedBenchIndices={selectedRackIndices}
              onSelectTile={index => {
                if (!isYourTurn || rackDisplay[index] === null) return;
                setSelectedRackIndices(current =>
                  current.includes(index) ? current.filter(value => value !== index) : [...current, index],
                );
              }}
            />
          </div>

          <div className="control-panel">
            <button className="btn btn-submit" onClick={submitMove} disabled={!isYourTurn || busy}>Play</button>
            <button className="btn btn-recall" onClick={() => setPendingTiles([])} disabled={!pendingTiles.length || busy}>Recall</button>
            <button className="btn btn-shuffle" onClick={shuffleRack} disabled={Boolean(pendingTiles.length) || busy}>Shuffle</button>
            <button className="btn btn-swap" onClick={exchangeTiles} disabled={!isYourTurn || busy || Boolean(pendingTiles.length)}>Exchange</button>
            <button className="btn btn-bot" onClick={() => void runAction("pass")} disabled={!isYourTurn || busy || Boolean(pendingTiles.length)}>Pass</button>
          </div>
        </div>

        <div className="sidebar-column">
          <div className="panel players-panel">
            <h3>Players</h3>
            {snapshot.players.map((player, index) => (
              <div className={`player-row ${snapshot.activePlayer === index && snapshot.status === "active" ? "active" : ""}`} key={index}>
                <span>{player.name}{snapshot.you === index ? " (You)" : ""}</span>
                <strong>{player.score}</strong>
                <small>{player.tileCount} tiles</small>
              </div>
            ))}
            <div className="bag-status">Tiles in Bag: <strong>{snapshot.bagCount}</strong></div>
          </div>

          {snapshot.status === "waiting" && (
            <div className="panel invite-panel">
              <h3>Invite a Player</h3>
              <p>Code: <strong>{snapshot.joinCode}</strong></p>
              <input readOnly value={inviteUrl} />
              <button className="btn btn-bot" onClick={() => navigator.clipboard.writeText(inviteUrl)}>Copy Invite Link</button>
            </div>
          )}

          {feedback && <div className={`feedback-alert feedback-${feedback.type}`}>{feedback.text}</div>}

          <div className="panel word-log-panel">
            <h3>Game History</h3>
            {snapshot.moves.length === 0 ? <p className="no-history">No turns yet.</p> : (
              <div className="log-list">
                {snapshot.moves.map(move => (
                  <div className="log-item" key={move.turn}>
                    <span className="log-word">
                      {move.player}: {move.action === "play" ? move.words.join(", ") : move.action}
                    </span>
                    <span className="log-points">{move.score ? `+${move.score}` : "—"}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="panel game-actions-panel">
            <button
              className="btn btn-recall"
              disabled={snapshot.status !== "active" || busy}
              onClick={() => window.confirm("Resign this game?") && void runAction("resign")}
            >Resign</button>
            <button className="text-button" onClick={() => {
              window.history.replaceState({}, "", window.location.pathname);
              setSnapshot(null);
              setGameReference(null);
              setToken(null);
            }}>Return to lobby</button>
          </div>
        </div>
      </div>
    </div>
  );
}


function Lobby({
  gameReference,
  busy,
  feedback,
  onCreate,
  onJoin,
}: {
  gameReference: string | null;
  busy: boolean;
  feedback: Feedback | null;
  onCreate: (mode: "human" | "bot", name: string) => Promise<void>;
  onJoin: (reference: string, name: string) => Promise<void>;
}) {
  const [name, setName] = useState(localStorage.getItem("scrabble:player-name") || "");
  const [joinReference, setJoinReference] = useState(gameReference || "");
  const rememberName = () => localStorage.setItem("scrabble:player-name", name.trim());

  return (
    <div className="lobby-shell">
      <div className="lobby-card">
        <h1>Oh My Pi Scrabble</h1>
        <p>Play a private game with a friend or challenge the GADDAG bot.</p>
        <label>
          Display name
          <input value={name} maxLength={30} onChange={event => setName(event.target.value)} placeholder="Your name" />
        </label>
        {gameReference ? (
          <button className="btn btn-submit" disabled={busy || !name.trim()} onClick={() => {
            rememberName();
            void onJoin(gameReference, name);
          }}>Join This Game</button>
        ) : (
          <div className="lobby-actions">
            <button className="btn btn-submit" disabled={busy || !name.trim()} onClick={() => {
              rememberName();
              void onCreate("human", name);
            }}>Create Friend Game</button>
            <button className="btn btn-bot" disabled={busy || !name.trim()} onClick={() => {
              rememberName();
              void onCreate("bot", name);
            }}>Play the Bot</button>
          </div>
        )}
        {!gameReference && (
          <div className="join-code-row">
            <input value={joinReference} onChange={event => setJoinReference(event.target.value)} placeholder="Game code" />
            <button className="btn btn-swap" disabled={busy || !name.trim() || !joinReference.trim()} onClick={() => {
              rememberName();
              void onJoin(joinReference.trim(), name);
            }}>Join</button>
          </div>
        )}
        {busy && <div className="feedback-alert feedback-info">Connecting…</div>}
        {feedback && <div className={`feedback-alert feedback-${feedback.type}`}>{feedback.text}</div>}
      </div>
    </div>
  );
}
