from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


BOARD_SIZE = 15
LETTER_VALUES = {
    "A": 1, "B": 3, "C": 3, "D": 2, "E": 1, "F": 4, "G": 2,
    "H": 4, "I": 1, "J": 8, "K": 5, "L": 1, "M": 3, "N": 1,
    "O": 1, "P": 3, "Q": 10, "R": 1, "S": 1, "T": 1, "U": 1,
    "V": 4, "W": 4, "X": 8, "Y": 4, "Z": 10,
}
T, D, TL, DL, N = "triple_word", "double_word", "triple_letter", "double_letter", "none"
BOARD_MULTIPLIERS = [
    [TL,N,N,T,N,N,N,DL,N,N,N,T,N,N,TL],
    [N,D,N,N,N,N,TL,N,TL,N,N,N,N,D,N],
    [N,N,N,N,DL,N,N,N,N,N,DL,N,N,N,N],
    [T,N,N,DL,N,N,N,D,N,N,N,DL,N,N,T],
    [N,N,DL,N,N,TL,N,N,N,TL,N,N,DL,N,N],
    [N,N,N,N,TL,N,N,DL,N,N,TL,N,N,N,N],
    [N,TL,N,N,N,N,N,N,N,N,N,N,N,TL,N],
    [DL,N,N,D,N,DL,N,N,N,DL,N,D,N,N,DL],
    [N,TL,N,N,N,N,N,N,N,N,N,N,N,TL,N],
    [N,N,N,N,TL,N,N,DL,N,N,TL,N,N,N,N],
    [N,N,DL,N,N,TL,N,N,N,TL,N,N,DL,N,N],
    [T,N,N,DL,N,N,N,D,N,N,N,DL,N,N,T],
    [N,N,N,N,DL,N,N,N,N,N,DL,N,N,N,N],
    [N,D,N,N,N,N,TL,N,TL,N,N,N,N,D,N],
    [TL,N,N,T,N,N,N,DL,N,N,N,T,N,N,TL],
]
TILE_DISTRIBUTION = {
    "A": 9, "B": 2, "C": 2, "D": 4, "E": 12, "F": 2, "G": 3,
    "H": 2, "I": 9, "J": 1, "K": 1, "L": 4, "M": 2, "N": 6,
    "O": 8, "P": 2, "Q": 1, "R": 6, "S": 4, "T": 6, "U": 4,
    "V": 2, "W": 2, "X": 1, "Y": 2, "Z": 1, "?": 2,
}


class RuleError(ValueError):
    pass


@dataclass
class MoveEvaluation:
    score: int
    words: list[str]
    placements: list[dict[str, Any]]
    modifiers: list[dict[str, Any]]


_dictionary: set[str] | None = None


def load_dictionary() -> set[str]:
    global _dictionary
    if _dictionary is None:
        path = Path(__file__).with_name("words.txt")
        _dictionary = {
            word.strip().upper()
            for word in path.read_text(encoding="utf-8").splitlines()
            if word.strip().isalpha()
        }
    return _dictionary


def create_board() -> list[list[dict[str, Any]]]:
    return [
        [
            {"multiplier": BOARD_MULTIPLIERS[r][c], "letter": None, "isLocked": False, "isBlank": False}
            for c in range(BOARD_SIZE)
        ]
        for r in range(BOARD_SIZE)
    ]


def create_bag() -> list[str]:
    return [letter for letter, count in TILE_DISTRIBUTION.items() for _ in range(count)]


def draw_tiles(bag: list[str], rack: list[str], target: int = 7) -> None:
    while len(rack) < target and bag:
        rack.append(bag.pop())


def remove_rack_tiles(rack: list[str], placements: list[dict[str, Any]]) -> list[str]:
    remaining = list(rack)
    consumed: list[str] = []
    for placement in placements:
        rack_letter = "?" if placement["isBlank"] else placement["letter"]
        try:
            remaining.remove(rack_letter)
        except ValueError as exc:
            raise RuleError(f"Rack does not contain required tile {rack_letter}.") from exc
        consumed.append(rack_letter)
    rack[:] = remaining
    return consumed


def remove_exchange_tiles(rack: list[str], requested: list[str]) -> list[str]:
    normalized = [tile.upper() for tile in requested]
    available = Counter(rack)
    needed = Counter(normalized)
    if any(needed[tile] > available[tile] for tile in needed):
        raise RuleError("Selected exchange tiles are not all present in the rack.")
    for tile in normalized:
        rack.remove(tile)
    return normalized


def rack_value(rack: list[str]) -> int:
    return sum(LETTER_VALUES.get(tile, 0) for tile in rack)


def evaluate_move(
    board: list[list[dict[str, Any]]],
    raw_placements: list[dict[str, Any]],
) -> MoveEvaluation:
    if not raw_placements:
        raise RuleError("Place at least one tile.")

    placements: list[dict[str, Any]] = []
    occupied: set[tuple[int, int]] = set()
    for raw in raw_placements:
        try:
            r, c = int(raw["r"]), int(raw["c"])
            letter = str(raw["letter"]).strip().upper()
            is_blank = bool(raw.get("isBlank", False))
        except (KeyError, TypeError, ValueError) as exc:
            raise RuleError("Each placement requires a row, column, and letter.") from exc
        if not (0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE):
            raise RuleError("A tile is outside the board.")
        if len(letter) != 1 or letter not in LETTER_VALUES:
            raise RuleError("Placed letters must be A through Z.")
        if (r, c) in occupied:
            raise RuleError("Two tiles cannot occupy the same square.")
        if board[r][c]["letter"] is not None:
            raise RuleError("A new tile cannot cover an existing tile.")
        occupied.add((r, c))
        placements.append({"r": r, "c": c, "letter": letter, "isBlank": is_blank})

    rows = {p["r"] for p in placements}
    cols = {p["c"] for p in placements}
    if len(rows) > 1 and len(cols) > 1:
        raise RuleError("Tiles must be placed in one row or column.")

    if len(placements) == 1:
        p = placements[0]
        horizontal_length = _segment(board, occupied, p["r"], p["c"], "H")
        vertical_length = _segment(board, occupied, p["r"], p["c"], "V")
        direction = "H" if len(horizontal_length) >= len(vertical_length) else "V"
    else:
        direction = "H" if len(rows) == 1 else "V"

    by_position = {(p["r"], p["c"]): p for p in placements}
    _ensure_no_gaps(board, by_position, direction)

    board_was_empty = not any(cell["letter"] is not None for row in board for cell in row)
    if board_was_empty:
        if (7, 7) not in occupied:
            raise RuleError("The first word must cover the center square.")
    elif not any(
        0 <= nr < BOARD_SIZE
        and 0 <= nc < BOARD_SIZE
        and board[nr][nc]["letter"] is not None
        for r, c in occupied
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
    ):
        raise RuleError("The move must connect to an existing tile.")

    words: list[list[tuple[int, int]]] = []
    first = placements[0]
    main = _segment(board, occupied, first["r"], first["c"], direction)
    if len(main) > 1:
        words.append(main)
    cross_direction = "V" if direction == "H" else "H"
    for placement in placements:
        cross = _segment(board, occupied, placement["r"], placement["c"], cross_direction)
        if len(cross) > 1:
            words.append(cross)
    if not words:
        raise RuleError("Tiles must form a word of at least two letters.")

    word_strings = [
        "".join(by_position.get(pos, board[pos[0]][pos[1]])["letter"] for pos in cells)
        for cells in words
    ]
    dictionary = load_dictionary()
    invalid = [word for word in word_strings if word not in dictionary]
    if invalid:
        raise RuleError(f"Invalid word{'s' if len(invalid) > 1 else ''}: {', '.join(invalid)}")

    score = sum(_score_word(board, by_position, cells) for cells in words)
    if len(placements) == 7:
        score += 50
    modifiers = [
        {"r": placement["r"], "c": placement["c"], "multiplier": board[placement["r"]][placement["c"]]["multiplier"]}
        for placement in placements
        if board[placement["r"]][placement["c"]]["multiplier"] != N
    ]
    return MoveEvaluation(score=score, words=word_strings, placements=placements, modifiers=modifiers)


def apply_move(board: list[list[dict[str, Any]]], placements: list[dict[str, Any]]) -> None:
    for placement in placements:
        square = board[placement["r"]][placement["c"]]
        square["letter"] = placement["letter"]
        square["isBlank"] = placement["isBlank"]
        square["isLocked"] = True


def _ensure_no_gaps(board: list[list[dict[str, Any]]], placements: dict[tuple[int, int], Any], direction: str) -> None:
    positions = list(placements)
    if direction == "H":
        r = positions[0][0]
        low, high = min(c for _, c in positions), max(c for _, c in positions)
        if any(board[r][c]["letter"] is None and (r, c) not in placements for c in range(low, high + 1)):
            raise RuleError("There cannot be gaps between placed tiles.")
    else:
        c = positions[0][1]
        low, high = min(r for r, _ in positions), max(r for r, _ in positions)
        if any(board[r][c]["letter"] is None and (r, c) not in placements for r in range(low, high + 1)):
            raise RuleError("There cannot be gaps between placed tiles.")


def _segment(
    board: list[list[dict[str, Any]]],
    placed: set[tuple[int, int]],
    r: int,
    c: int,
    direction: str,
) -> list[tuple[int, int]]:
    dr, dc = (0, 1) if direction == "H" else (1, 0)

    def filled(rr: int, cc: int) -> bool:
        return 0 <= rr < BOARD_SIZE and 0 <= cc < BOARD_SIZE and (
            board[rr][cc]["letter"] is not None or (rr, cc) in placed
        )

    start_r, start_c = r, c
    while filled(start_r - dr, start_c - dc):
        start_r -= dr
        start_c -= dc
    cells: list[tuple[int, int]] = []
    while filled(start_r, start_c):
        cells.append((start_r, start_c))
        start_r += dr
        start_c += dc
    return cells


def _score_word(
    board: list[list[dict[str, Any]]],
    placements: dict[tuple[int, int], dict[str, Any]],
    cells: list[tuple[int, int]],
) -> int:
    total, word_multiplier = 0, 1
    for r, c in cells:
        if (r, c) in placements:
            placement = placements[(r, c)]
            value = 0 if placement["isBlank"] else LETTER_VALUES[placement["letter"]]
            multiplier = board[r][c]["multiplier"]
            if multiplier == DL:
                value *= 2
            elif multiplier == TL:
                value *= 3
            elif multiplier == D:
                word_multiplier *= 2
            elif multiplier == T:
                word_multiplier *= 3
            total += value
        else:
            square = board[r][c]
            total += 0 if square.get("isBlank") else LETTER_VALUES[square["letter"]]
    return total * word_multiplier
