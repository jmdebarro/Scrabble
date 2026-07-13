from __future__ import annotations
import os
import time
import random
from collections import Counter

FLIP_RIGHT = "<"
WORD_END = "$"

# Face values of Scrabble tiles
LETTER_VALUES = {
    'A': 1, 'B': 3, 'C': 3, 'D': 2, 'E': 1, 'F': 4, 'G': 2, 'H': 4, 'I': 1,
    'J': 8, 'K': 5, 'L': 1, 'M': 3, 'N': 1, 'O': 1, 'P': 3, 'Q': 10, 'R': 1,
    'S': 1, 'T': 1, 'U': 1, 'V': 4, 'W': 4, 'X': 8, 'Y': 4, 'Z': 10
}

# Standard Scrabble board premium multiplier definitions
DL = "DL"  # Double Letter
TL = "TL"  # Triple Letter
DW = "DW"  # Double Word
TW = "TW"  # Triple Word
__ = "none"  # Normal square

BOARD_MULTIPLIERS = [
    [TW, __, __, DL, __, __, __, TW, __, __, __, DL, __, __, TW],
    [__, DW, __, __, __, TL, __, __, __, TL, __, __, __, DW, __],
    [__, __, DW, __, __, __, DL, __, DL, __, __, __, DW, __, __],
    [DL, __, __, DW, __, __, __, DL, __, __, __, DW, __, __, DL],
    [__, __, __, __, DW, __, __, __, __, __, DW, __, __, __, __],
    [__, TL, __, __, __, TL, __, __, __, TL, __, __, __, TL, __],
    [__, __, DL, __, __, __, DL, __, DL, __, __, __, DL, __, __],
    [TW, __, __, DL, __, __, __, DW, __, __, __, DL, __, __, TW],
    [__, __, DL, __, __, __, DL, __, DL, __, __, __, DL, __, __],
    [__, TL, __, __, __, TL, __, __, __, TL, __, __, __, TL, __],
    [__, __, __, __, DW, __, __, __, __, __, DW, __, __, __, __],
    [DL, __, __, DW, __, __, __, DL, __, __, __, DW, __, __, DL],
    [__, __, DW, __, __, __, DL, __, DL, __, __, __, DW, __, __],
    [__, DW, __, __, __, TL, __, __, __, TL, __, __, __, DW, __],
    [TW, __, __, DL, __, __, __, TW, __, __, __, DL, __, __, TW],
]

# Static rack leave values inspired by tournament engine equities
RACK_LEAVE_EQUITIES = {
    'A': 1.5, 'B': -2.0, 'C': 0.5, 'D': 1.0, 'E': 2.5, 'F': -1.5, 'G': -1.0,
    'H': 1.0, 'I': 1.0, 'J': -3.0, 'K': -1.5, 'L': 1.5, 'M': 1.0, 'N': 2.0,
    'O': 1.5, 'P': 1.0, 'Q': -4.5, 'R': 2.5, 'S': 7.5, 'T': 2.5, 'U': 0.5,
    'V': -4.0, 'W': -2.5, 'X': 3.0, 'Y': -0.5, 'Z': 2.5, '?': 25.0
}

class GADDAG:
    """
    Optimized GADDAG dictionary structure for extremely fast bidirectional Scrabble move generation.
    Each variation of a word is inserted to allow starting search from any anchor letter.
    """
    def __init__(self):
        self.root = {}

    def insert_variation(self, variation: str):
        cur_node = self.root
        for char in variation:
            if char not in cur_node:
                cur_node[char] = {}
            cur_node = cur_node[char]

    def insert_word(self, word: str):
        word = word.strip().upper()
        if not word:
            return
        
        variations = self.create_word_variations(word)
        for var in variations:
            self.insert_variation(var)

    @staticmethod
    def create_word_variations(s: str) -> list[str]:
        variations = []
        length = len(s)
        for i in range(length):
            left_part = s[i]
            prev = i - 1
            while prev >= 0:
                left_part += s[prev]
                prev -= 1
            
            right_part = ""
            if i < length - 1:
                right_part = s[i+1:]
                
            variation = f"{left_part}{FLIP_RIGHT}{right_part}{WORD_END}"
            variations.append(variation)
        return variations

    def load_dictionary(self, filepath: str, max_words: int = None):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Dictionary file not found at: {filepath}")
            
        print(f"Loading GADDAG from {filepath}...")
        start_time = time.time()
        
        count = 0
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                word = line.strip().upper()
                if not word or not word.isalpha():
                    continue
                self.insert_word(word)
                count += 1
                if max_words and count >= max_words:
                    break
                    
        elapsed = time.time() - start_time
        print(f"Loaded {count} words in {elapsed:.2f} seconds.")

    def contains(self, word: str) -> bool:
        word = word.strip().upper()
        if not word:
            return False
        variation = f"{word[0]}{FLIP_RIGHT}{word[1:]}{WORD_END}"
        
        cur_node = self.root
        for char in variation:
            if char not in cur_node:
                return False
            cur_node = cur_node[char]
        return True


class BoardState:
    SIZE = 15

    def __init__(self):
        self.grid = [[None for _ in range(self.SIZE)] for _ in range(self.SIZE)]

    def set_tile(self, r: int, c: int, letter: str):
        if 0 <= r < self.SIZE and 0 <= c < self.SIZE:
            self.grid[r][c] = letter.strip().upper()

    def get_tile(self, r: int, c: int) -> str | None:
        if 0 <= r < self.SIZE and 0 <= c < self.SIZE:
            return self.grid[r][c]
        return None

    def get_anchors(self) -> list[tuple[int, int]]:
        anchors = []
        is_empty = True
        
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                if self.grid[r][c] is not None:
                    is_empty = False
                    break
            if not is_empty:
                break

        if is_empty:
            return [(7, 7)]

        for r in range(self.SIZE):
            for c in range(self.SIZE):
                if self.grid[r][c] is None:
                    adjacent = [
                        (r - 1, c), (r + 1, c),
                        (r, c - 1), (r, c + 1)
                    ]
                    for nr, nc in adjacent:
                        if 0 <= nr < self.SIZE and 0 <= nc < self.SIZE:
                            if self.grid[nr][nc] is not None:
                                anchors.append((r, c))
                                break
        return anchors

    def compute_vertical_cross_checks(self, gaddag: GADDAG) -> dict[tuple[int, int], set[str]]:
        cross_checks = {}
        alphabet = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

        for r in range(self.SIZE):
            for c in range(self.SIZE):
                if self.grid[r][c] is not None:
                    continue

                up_parts = []
                curr_r = r - 1
                while curr_r >= 0 and self.grid[curr_r][c] is not None:
                    up_parts.append(self.grid[curr_r][c])
                    curr_r -= 1
                up_str = "".join(reversed(up_parts))

                down_parts = []
                curr_r = r + 1
                while curr_r < self.SIZE and self.grid[curr_r][c] is not None:
                    down_parts.append(self.grid[curr_r][c])
                    curr_r += 1
                down_str = "".join(down_parts)

                if not up_str and not down_str:
                    cross_checks[(r, c)] = alphabet
                else:
                    valid_letters = set()
                    for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                        candidate_word = f"{up_str}{char}{down_str}"
                        if gaddag.contains(candidate_word):
                            valid_letters.add(char)
                    cross_checks[(r, c)] = valid_letters

        return cross_checks

    def compute_horizontal_cross_checks(self, gaddag: GADDAG) -> dict[tuple[int, int], set[str]]:
        cross_checks = {}
        alphabet = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

        for r in range(self.SIZE):
            for c in range(self.SIZE):
                if self.grid[r][c] is not None:
                    continue

                left_parts = []
                curr_c = c - 1
                while curr_c >= 0 and self.grid[r][curr_c] is not None:
                    left_parts.append(self.grid[r][curr_c])
                    curr_c -= 1
                left_str = "".join(reversed(left_parts))

                right_parts = []
                curr_c = c + 1
                while curr_c < self.SIZE and self.grid[r][curr_c] is not None:
                    right_parts.append(self.grid[r][curr_c])
                    curr_c += 1
                right_str = "".join(right_parts)

                if not left_str and not right_str:
                    cross_checks[(r, c)] = alphabet
                else:
                    valid_letters = set()
                    for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                        candidate_word = f"{left_str}{char}{right_str}"
                        if gaddag.contains(candidate_word):
                            valid_letters.add(char)
                    cross_checks[(r, c)] = valid_letters

        return cross_checks

    def transpose(self) -> BoardState:
        transposed = BoardState()
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                transposed.grid[c][r] = self.grid[r][c]
        return transposed


class Move:
    def __init__(self, word: str, r: int, c: int, direction: str, tiles_placed: list[tuple[int, int, str, bool]]):
        self.word = word
        self.r = r  # Starting row of the word
        self.c = c  # Starting col of the word
        self.direction = direction  # 'H' (horizontal) or 'V' (vertical)
        # List of tuples: (row, col, letter, is_blank)
        self.tiles_placed = tiles_placed

    def __repr__(self) -> str:
        return f"Move(word='{self.word}', start=({self.r},{self.c}), dir='{self.direction}', placed={len(self.tiles_placed)} tiles)"


class MoveGenerator:
    def __init__(self, gaddag: GADDAG):
        self.gaddag = gaddag

    def generate_all_moves(self, board: BoardState, rack: list[str]) -> list[Move]:
        rack = [char.upper() for char in rack]
        
        horizontal_moves = self._generate_horizontal_moves(board, rack, direction="H")
        
        transposed_board = board.transpose()
        transposed_moves = self._generate_horizontal_moves(transposed_board, rack, direction="V")
        
        vertical_moves = []
        for move in transposed_moves:
            orig_r = move.c
            orig_c = move.r
            orig_tiles_placed = [
                (col, row, letter, is_blank)
                for row, col, letter, is_blank in move.tiles_placed
            ]
            vertical_moves.append(Move(move.word, orig_r, orig_c, "V", orig_tiles_placed))
            
        return horizontal_moves + vertical_moves

    def _generate_horizontal_moves(self, board: BoardState, rack: list[str], direction: str) -> list[Move]:
        moves = []
        anchors = board.get_anchors()
        cross_checks = board.compute_vertical_cross_checks(self.gaddag)
        
        rack_counts = Counter(rack)

        for anchor_r, anchor_c in anchors:
            for letter in list(rack_counts.keys()):
                if letter == "?":
                    for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                        if char in self.gaddag.root and char in cross_checks[(anchor_r, anchor_c)]:
                            new_rack = Counter(rack_counts)
                            new_rack["?"] -= 1
                            if new_rack["?"] == 0:
                                del new_rack["?"]
                            self._search_left(
                                board, anchor_r, anchor_c, anchor_c,
                                self.gaddag.root[char], new_rack,
                                [(anchor_r, anchor_c, char, True)],
                                cross_checks, moves, direction
                            )
                else:
                    if letter in self.gaddag.root and letter in cross_checks[(anchor_r, anchor_c)]:
                        new_rack = Counter(rack_counts)
                        new_rack[letter] -= 1
                        if new_rack[letter] == 0:
                            del new_rack[letter]
                        self._search_left(
                            board, anchor_r, anchor_c, anchor_c,
                            self.gaddag.root[letter], new_rack,
                            [(anchor_r, anchor_c, letter, False)],
                            cross_checks, moves, direction
                        )
        return moves

    def _search_left(
        self, board: BoardState, r: int, anchor_c: int, curr_c: int,
        node: dict, rack: Counter, tiles_placed: list[tuple[int, int, str, bool]],
        cross_checks: dict, moves: list[Move], direction: str
    ):
        next_c = curr_c - 1
        
        if next_c >= 0:
            tile = board.get_tile(r, next_c)
            if tile is not None:
                if tile in node:
                    self._search_left(board, r, anchor_c, next_c, node[tile], rack, tiles_placed, cross_checks, moves, direction)
            else:
                if FLIP_RIGHT in node:
                    self._search_right(board, r, anchor_c, anchor_c, node[FLIP_RIGHT], rack, tiles_placed, cross_checks, moves, direction)
                
                for letter in list(rack.keys()):
                    if letter == "?":
                        for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                            if char in node and char in cross_checks[(r, next_c)]:
                                new_rack = Counter(rack)
                                new_rack["?"] -= 1
                                if new_rack["?"] == 0:
                                    del new_rack["?"]
                                self._search_left(
                                    board, r, anchor_c, next_c,
                                    node[char], new_rack,
                                    tiles_placed + [(r, next_c, char, True)],
                                    cross_checks, moves, direction
                                )
                    else:
                        if letter in node and letter in cross_checks[(r, next_c)]:
                            new_rack = Counter(rack)
                            new_rack[letter] -= 1
                            if new_rack[letter] == 0:
                                del new_rack[letter]
                            self._search_left(
                                board, r, anchor_c, next_c,
                                node[letter], new_rack,
                                tiles_placed + [(r, next_c, letter, False)],
                                cross_checks, moves, direction
                            )
        else:
            if FLIP_RIGHT in node:
                self._search_right(board, r, anchor_c, anchor_c, node[FLIP_RIGHT], rack, tiles_placed, cross_checks, moves, direction)

    def _search_right(
        self, board: BoardState, r: int, anchor_c: int, curr_c: int,
        node: dict, rack: Counter, tiles_placed: list[tuple[int, int, str, bool]],
        cross_checks: dict, moves: list[Move], direction: str
    ):
        next_c = curr_c + 1
        
        if WORD_END in node:
            if len(tiles_placed) > 0:
                if next_c >= BoardState.SIZE or board.get_tile(r, next_c) is None:
                    start_c = anchor_c
                    while start_c > 0 and (board.get_tile(r, start_c - 1) is not None or any(tp[1] == start_c - 1 for tp in tiles_placed)):
                        start_c -= 1
                    
                    end_c = anchor_c
                    while end_c < BoardState.SIZE - 1 and (board.get_tile(r, end_c + 1) is not None or any(tp[1] == end_c + 1 for tp in tiles_placed)):
                        end_c += 1
                        
                    word_chars = []
                    for c in range(start_c, end_c + 1):
                        bt = board.get_tile(r, c)
                        if bt is not None:
                            word_chars.append(bt)
                        else:
                            placed_char = next(tp[2] for tp in tiles_placed if tp[1] == c)
                            word_chars.append(placed_char)
                            
                    full_word = "".join(word_chars)
                    moves.append(Move(full_word, r, start_c, direction, tiles_placed))

        if next_c < BoardState.SIZE:
            tile = board.get_tile(r, next_c)
            if tile is not None:
                if tile in node:
                    self._search_right(board, r, anchor_c, next_c, node[tile], rack, tiles_placed, cross_checks, moves, direction)
            else:
                for letter in list(rack.keys()):
                    if letter == "?":
                        for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                            if char in node and char in cross_checks[(r, next_c)]:
                                new_rack = Counter(rack)
                                new_rack["?"] -= 1
                                if new_rack["?"] == 0:
                                    del new_rack["?"]
                                self._search_right(
                                    board, r, anchor_c, next_c,
                                    node[char], new_rack,
                                    tiles_placed + [(r, next_c, char, True)],
                                    cross_checks, moves, direction
                                )
                    else:
                        if letter in node and letter in cross_checks[(r, next_c)]:
                            new_rack = Counter(rack)
                            new_rack[letter] -= 1
                            if new_rack[letter] == 0:
                                del new_rack[letter]
                            self._search_right(
                                board, r, anchor_c, next_c,
                                node[letter], new_rack,
                                tiles_placed + [(r, next_c, letter, False)],
                                cross_checks, moves, direction
                            )


class MoveScorer:
    """
    Evaluates moves according to official Scrabble rules,
    and applies strategic heuristics (rack leave equity, duplicate vowel/consonant penalties, 
    and opponent multiplier exposure defense).
    """
    
    @staticmethod
    def score_move(board: BoardState, move: Move) -> int:
        placed_map = {(tp[0], tp[1]): (tp[2], tp[3]) for tp in move.tiles_placed}
        
        def score_word_segment(start_r: int, start_c: int, end_r: int, end_c: int, direction: str) -> int:
            total = 0
            word_mult = 1
            
            curr_r, curr_c = start_r, start_c
            while True:
                existing_tile = board.get_tile(curr_r, curr_c)
                
                if existing_tile is not None:
                    total += LETTER_VALUES.get(existing_tile, 0)
                else:
                    char, is_blank = placed_map[(curr_r, curr_c)]
                    val = 0 if is_blank else LETTER_VALUES.get(char, 0)
                    
                    mult = BOARD_MULTIPLIERS[curr_r][curr_c]
                    if mult == DL:
                        total += val * 2
                    elif mult == TL:
                        total += val * 3
                    elif mult == DW:
                        total += val
                        word_mult *= 2
                    elif mult == TW:
                        total += val
                        word_mult *= 3
                    else:
                        total += val
                
                if direction == "H":
                    if curr_c == end_c: break
                    curr_c += 1
                else:
                    if curr_r == end_r: break
                    curr_r += 1
                    
            return total * word_mult

        total_score = 0
        
        if move.direction == "H":
            r = move.r
            start_c = move.c
            end_c = start_c
            while end_c < BoardState.SIZE - 1 and (board.get_tile(r, end_c + 1) is not None or (r, end_c + 1) in placed_map):
                end_c += 1
            primary_score = score_word_segment(r, start_c, r, end_c, "H")
            total_score += primary_score
        else:
            c = move.c
            start_r = move.r
            end_r = start_r
            while end_r < BoardState.SIZE - 1 and (board.get_tile(end_r + 1, c) is not None or (end_r + 1, c) in placed_map):
                end_r += 1
            primary_score = score_word_segment(start_r, c, end_r, c, "V")
            total_score += primary_score

        for tr, tc, char, is_blank in move.tiles_placed:
            if move.direction == "H":
                up_parts = []
                curr_r = tr - 1
                while curr_r >= 0 and board.get_tile(curr_r, tc) is not None:
                    up_parts.append(curr_r)
                    curr_r -= 1
                
                down_parts = []
                curr_r = tr + 1
                while curr_r < BoardState.SIZE and board.get_tile(curr_r, tc) is not None:
                    down_parts.append(curr_r)
                    curr_r += 1
                    
                if up_parts or down_parts:
                    start_r = min(up_parts) if up_parts else tr
                    end_r = max(down_parts) if down_parts else tr
                    total_score += score_word_segment(start_r, tc, end_r, tc, "V")
            else:
                left_parts = []
                curr_c = tc - 1
                while curr_c >= 0 and board.get_tile(tr, curr_c) is not None:
                    left_parts.append(curr_c)
                    curr_c -= 1
                
                right_parts = []
                curr_c = tc + 1
                while curr_c < BoardState.SIZE and board.get_tile(tr, curr_c) is not None:
                    right_parts.append(curr_c)
                    curr_c += 1
                    
                if left_parts or right_parts:
                    start_c = min(left_parts) if left_parts else tc
                    end_c = max(right_parts) if right_parts else tc
                    total_score += score_word_segment(tr, start_c, tr, end_c, "H")

        if len(move.tiles_placed) == 7:
            total_score += 50
            
        return total_score

    @staticmethod
    def evaluate_move(board: BoardState, move: Move, original_rack: list[str]) -> float:
        score = MoveScorer.score_move(board, move)
        
        remaining_rack = list(original_rack)
        for tr, tc, char, is_blank in move.tiles_placed:
            ref_letter = "?" if is_blank else char
            if ref_letter in remaining_rack:
                remaining_rack.remove(ref_letter)
                
        rack_equity = sum(RACK_LEAVE_EQUITIES.get(ch, 0) for ch in remaining_rack)
        
        vowels_list = "AEIOU"
        vowels_count = sum(1 for ch in remaining_rack if ch in vowels_list)
        consonants_count = sum(1 for ch in remaining_rack if ch != "?" and ch not in vowels_list)
        
        if len(remaining_rack) > 0:
            if vowels_count == 3 and consonants_count == 4:
                rack_equity += 3.0
            elif vowels_count == 4 and consonants_count == 3:
                rack_equity += 3.0
            elif vowels_count == 0 or consonants_count == 0:
                rack_equity -= 10.0
            elif vowels_count == 1 or consonants_count == 1:
                rack_equity -= 4.0
            elif vowels_count >= 5 or consonants_count >= 5:
                rack_equity -= 5.0
                
        counts = Counter(remaining_rack)
        for letter, count in counts.items():
            if count > 1 and letter != "?":
                rack_equity -= 2.5 * (count - 1)

        defense_penalty = 0.0
        adjacent_shifts = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        
        for tr, tc, _, _ in move.tiles_placed:
            for dr, dc in adjacent_shifts:
                nr, nc = tr + dr, tc + dc
                if 0 <= nr < BoardState.SIZE and 0 <= nc < BoardState.SIZE:
                    if board.get_tile(nr, nc) is None:
                        mult = BOARD_MULTIPLIERS[nr][nc]
                        if mult == TW:
                            defense_penalty += 12.0
                        elif mult == DW:
                            defense_penalty += 6.0
                        elif mult == TL:
                            defense_penalty += 4.0

        utility = score + rack_equity - defense_penalty
        return utility


class MonteCarloSolver:
    """
    Advanced multi-turn planning engine that executes random tile-bag rollouts 
    to calculate the actual Expected Value (EV) of top candidate plays.
    """
    def __init__(self, generator: MoveGenerator):
        self.generator = generator

    def select_best_move_mc(
        self, board: BoardState, rack: list[str], unseen_bag: list[str],
        top_k: int = 5, num_simulations: int = 15
    ) -> tuple[Move | None, float]:
        """
        Runs Monte Carlo simulations on the top_k candidate moves, 
        evaluating them against random draws for the opponent.
        Returns the (best_move, estimated_ev) tuple.
        """
        # 1. Generate all legal moves
        all_moves = self.generator.generate_all_moves(board, rack)
        if not all_moves:
            return None, 0.0

        # 2. Score them statically using our heuristics and sort them
        scored_moves = []
        for m in all_moves:
            utility = MoveScorer.evaluate_move(board, m, rack)
            scored_moves.append((m, utility))
            
        scored_moves.sort(key=lambda x: x[1], reverse=True)
        
        # Take the top K candidate moves to run rollouts on (reduces processing overhead)
        candidates = scored_moves[:top_k]
        if len(candidates) == 1:
            return candidates[0][0], candidates[0][1]

        best_move = None
        best_ev = -9999.0

        # 3. For each candidate, run rollouts
        for move, static_utility in candidates:
            total_score_diff = 0.0
            
            # Temporarily apply the play to a copy of the board
            sim_board = BoardState()
            for r in range(BoardState.SIZE):
                for c in range(BoardState.SIZE):
                    sim_board.grid[r][c] = board.grid[r][c]
                    
            # Place move's tiles on the simulated board
            for r, c, char, is_blank in move.tiles_placed:
                sim_board.set_tile(r, c, char)
                
            # Filter played letters from the unseen bag to represent remaining bag
            placed_letters = ["?" if is_blank else char for _, _, char, is_blank in move.tiles_placed]
            bag_after_play = list(unseen_bag)
            for char in placed_letters:
                if char in bag_after_play:
                    bag_after_play.remove(char)

            # Get our score for this play
            our_play_score = MoveScorer.score_move(board, move)

            # Run randomized rollouts
            for _ in range(num_simulations):
                if not bag_after_play:
                    # No tiles left to draw, opponent gets empty rack or whatever is left
                    total_score_diff += our_play_score
                    continue
                    
                # A. Randomly draw 7 tiles for the opponent from remaining bag
                random.shuffle(bag_after_play)
                opponent_rack = bag_after_play[:7]
                
                # B. Generate opponent plays on the modified board
                opponent_moves = self.generator.generate_all_moves(sim_board, opponent_rack)
                
                opponent_best_score = 0
                if opponent_moves:
                    # Opponent plays greedily/heuristically their highest-scoring response
                    scored_opp_moves = [
                        (op_m, MoveScorer.score_move(sim_board, op_m))
                        for op_m in opponent_moves
                    ]
                    opponent_best_score = max(x[1] for x in scored_opp_moves)
                    
                # C. Cumulative score difference
                total_score_diff += (our_play_score - opponent_best_score)
                
            avg_ev = total_score_diff / num_simulations
            
            # We also add a small weight of the rack leave equity to the EV
            placed_letters_set = [char for _, _, char, is_blank in move.tiles_placed]
            remaining_rack = list(rack)
            for tr, tc, char, is_blank in move.tiles_placed:
                ref_letter = "?" if is_blank else char
                if ref_letter in remaining_rack:
                    remaining_rack.remove(ref_letter)
            rack_leave_utility = sum(RACK_LEAVE_EQUITIES.get(ch, 0) for ch in remaining_rack)
            
            composite_ev = avg_ev + 0.5 * rack_leave_utility

            if composite_ev > best_ev:
                best_ev = composite_ev
                best_move = move
                
        return best_move, best_ev
