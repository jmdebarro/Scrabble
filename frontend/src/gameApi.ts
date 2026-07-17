import type { Square } from "./boardLogic";

export interface PlayerSummary {
  name: string;
  score: number;
  tileCount: number;
  isBot?: boolean;
}

export interface MoveSummary {
  turn: number;
  player: string;
  action: "play" | "exchange" | "pass" | "resign";
  score: number;
  words: string[];
  modifiers: { r: number; c: number; multiplier: string }[];
  details: Record<string, unknown>;
}

export interface GameSnapshot {
  gameId: string;
  joinCode: string;
  mode: "human" | "bot";
  status: "waiting" | "active" | "finished";
  version: number;
  board: Square[][];
  bagCount: number;
  rack: string[];
  you: number;
  activePlayer: number;
  players: PlayerSummary[];
  consecutiveScoreless: number;
  moves: MoveSummary[];
  winner: number | null;
  finishReason: string | null;
  updatedAt: string;
}

export interface GameSession {
  token: string;
  snapshot: GameSnapshot;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || body.error || `Request failed (${response.status})`);
  }
  return body as T;
}

export function createGame(mode: "human" | "bot", playerName: string): Promise<GameSession> {
  return request("/api/games", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode, playerName }),
  });
}

export function joinGame(reference: string, playerName: string): Promise<GameSession> {
  return request(`/api/games/${encodeURIComponent(reference)}/join`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ playerName }),
  });
}

export function loadGame(reference: string, token: string): Promise<GameSnapshot> {
  return request(`/api/games/${encodeURIComponent(reference)}`, {
    headers: { "X-Player-Token": token },
  });
}

export function sendAction(
  gameId: string,
  token: string,
  action: Record<string, unknown>,
): Promise<GameSnapshot> {
  return request(`/api/games/${encodeURIComponent(gameId)}/actions`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Player-Token": token },
    body: JSON.stringify(action),
  });
}

export function websocketUrl(gameId: string, token: string): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/api/games/${encodeURIComponent(gameId)}/events?token=${encodeURIComponent(token)}`;
}

export function tokenStorageKey(gameId: string): string {
  return `scrabble:player-token:${gameId}`;
}
