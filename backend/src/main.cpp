#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <algorithm>
#include <chrono>
#include <sstream>
#include <random>
#include <cmath>
using namespace std;

// Constants
const char FLIP_RIGHT = '<';
const char WORD_END = '$';
const int BOARD_SIZE = 15;

// Scrabble face values
const unordered_map<char, int> LETTER_VALUES = {
    {'A', 1}, {'B', 3}, {'C', 3}, {'D', 2}, {'E', 1}, {'F', 4}, {'G', 2}, {'H', 4}, {'I', 1},
    {'J', 8}, {'K', 5}, {'L', 1}, {'M', 3}, {'N', 1}, {'O', 1}, {'P', 3}, {'Q', 10}, {'R', 1},
    {'S', 1}, {'T', 1}, {'U', 1}, {'V', 4}, {'W', 4}, {'X', 8}, {'Y', 4}, {'Z', 10}
};

// Map letter values with array mapping for speed
int get_letter_value(char c) {
    if (c >= 'a' && c <= 'z') return 0; // lowercase means blank tile
    if (c >= 'A' && c <= 'Z') {
        auto it = LETTER_VALUES.find(c);
        if (it != LETTER_VALUES.end()) return it->second;
    }
    return 0;
}

// Board multipliers
const string DL = "DL"; // Double Letter
const string TL = "TL"; // Triple Letter
const string DW = "DW"; // Double Word
const string TW = "TW"; // Triple Word
const string NO = "none"; // Normal

const string BOARD_MULTIPLIERS[15][15] = {
    {TW, NO, NO, DL, NO, NO, NO, TW, NO, NO, NO, DL, NO, NO, TW},
    {NO, DW, NO, NO, NO, TL, NO, NO, NO, TL, NO, NO, NO, DW, NO},
    {NO, NO, DW, NO, NO, NO, DL, NO, DL, NO, NO, NO, DW, NO, NO},
    {DL, NO, NO, DW, NO, NO, NO, DL, NO, NO, NO, DW, NO, NO, DL},
    {NO, NO, NO, NO, DW, NO, NO, NO, NO, NO, DW, NO, NO, NO, NO},
    {NO, TL, NO, NO, NO, TL, NO, NO, NO, TL, NO, NO, NO, TL, NO},
    {NO, NO, DL, NO, NO, NO, DL, NO, DL, NO, NO, NO, DL, NO, NO},
    {TW, NO, NO, DL, NO, NO, NO, DW, NO, NO, NO, DL, NO, NO, TW},
    {NO, NO, DL, NO, NO, NO, DL, NO, DL, NO, NO, NO, DL, NO, NO},
    {NO, TL, NO, NO, NO, TL, NO, NO, NO, TL, NO, NO, NO, TL, NO},
    {NO, NO, NO, NO, DW, NO, NO, NO, NO, NO, DW, NO, NO, NO, NO},
    {DL, NO, NO, DW, NO, NO, NO, DL, NO, NO, NO, DW, NO, NO, DL},
    {NO, NO, DW, NO, NO, NO, DL, NO, DL, NO, NO, NO, DW, NO, NO},
    {NO, DW, NO, NO, NO, TL, NO, NO, NO, TL, NO, NO, NO, DW, NO},
    {TW, NO, NO, DL, NO, NO, NO, TW, NO, NO, NO, DL, NO, NO, TW}
};

// Static rack leave values inspired by tournament engine equities
const unordered_map<char, double> RACK_LEAVE_EQUITIES = {
    {'A', 1.5}, {'B', -2.0}, {'C', 0.5}, {'D', 1.0}, {'E', 2.5}, {'F', -1.5}, {'G', -1.0},
    {'H', 1.0}, {'I', 1.0}, {'J', -3.0}, {'K', -1.5}, {'L', 1.5}, {'M', 1.0}, {'N', 2.0},
    {'O', 1.5}, {'P', 1.0}, {'Q', -4.5}, {'R', 2.5}, {'S', 7.5}, {'T', 2.5}, {'U', 0.5},
    {'V', -4.0}, {'W', -2.5}, {'X', 3.0}, {'Y', -0.5}, {'Z', 2.5}, {'?', 25.0}
};

// Flat Cache-Friendly child-sibling representation of GADDAG
struct GADDAGNode {
    char character = 0;
    bool is_word = false;
    int first_child = -1;
    int next_sibling = -1;
};

class GADDAG {
public:
    vector<GADDAGNode> nodes;

    GADDAG() {
        // Root node
        GADDAGNode root;
        nodes.push_back(root);
    }

    void insert_variation(const string& variation) {
        int curr = 0;
        for (char c : variation) {
            int child = nodes[curr].first_child;
            int prev_sibling = -1;
            bool found = false;

            while (child != -1) {
                if (nodes[child].character == c) {
                    curr = child;
                    found = true;
                    break;
                }
                prev_sibling = child;
                child = nodes[child].next_sibling;
            }

            if (!found) {
                GADDAGNode new_node;
                new_node.character = c;
                int new_idx = nodes.size();
                nodes.push_back(new_node);

                if (prev_sibling == -1) {
                    nodes[curr].first_child = new_idx;
                } else {
                    nodes[prev_sibling].next_sibling = new_idx;
                }
                curr = new_idx;
            }
        }
        nodes[curr].is_word = true;
    }

    void insert_word(const string& word) {
        int len = word.length();
        for (int i = 0; i < len; ++i) {
            // Prefix reversed
            string prefix = "";
            prefix += word[i];
            for (int prev = i - 1; prev >= 0; --prev) {
                prefix += word[prev];
            }
            // Suffix normal
            string suffix = "";
            if (i < len - 1) {
                suffix = word.substr(i + 1);
            }
            string var = prefix + FLIP_RIGHT + suffix + WORD_END;
            insert_variation(var);
        }
    }

    void load_dictionary(const string& filepath, int max_words = 0) {
        ifstream f(filepath);
        if (!f.is_open()) return;
        string line;
        int count = 0;
        while (getline(f, line)) {
            // Trim whitespace
            while (!line.empty() && (line.back() == '\r' || line.back() == '\n' || line.back() == ' ')) {
                line.pop_back();
            }
            if (line.empty()) continue;
            // Ensure uppercase alphabetical
            bool valid = true;
            for (char& c : line) {
                c = toupper(c);
                if (c < 'A' || c > 'Z') valid = false;
            }
            if (!valid) continue;
            insert_word(line);
            count++;
            if (max_words > 0 && count >= max_words) break;
        }
    }

    bool contains(const string& word) const {
        if (word.empty()) return false;
        string variation = "";
        variation += word[0];
        variation += FLIP_RIGHT;
        variation += word.substr(1);
        variation += WORD_END;

        int curr = 0;
        for (char c : variation) {
            int child = nodes[curr].first_child;
            bool found = false;
            while (child != -1) {
                if (nodes[child].character == c) {
                    curr = child;
                    found = true;
                    break;
                }
                child = nodes[child].next_sibling;
            }
            if (!found) return false;
        }
        return nodes[curr].is_word;
    }

    // Quick helper to traverse children
    int get_child(int node_idx, char c) const {
        int child = nodes[node_idx].first_child;
        while (child != -1) {
            if (nodes[child].character == c) return child;
            child = nodes[child].next_sibling;
        }
        return -1;
    }
};

class BoardState {
public:
    char grid[15][15];
    bool blank_grid[15][15];

    BoardState() {
        for (int r = 0; r < 15; r++) {
            for (int c = 0; c < 15; c++) {
                grid[r][c] = 0;
                blank_grid[r][c] = false;
            }
        }
    }

    void set_tile(int r, int c, char letter, bool is_blank = false) {
        if (r >= 0 && r < 15 && c >= 0 && c < 15) {
            grid[r][c] = toupper(letter);
            blank_grid[r][c] = is_blank;
        }
    }

    char get_tile(int r, int c) const {
        if (r >= 0 && r < 15 && c >= 0 && c < 15) {
            return grid[r][c];
        }
        return 0;
    }

    bool is_blank(int r, int c) const {
        return r >= 0 && r < 15 && c >= 0 && c < 15 && blank_grid[r][c];
    }

    vector<pair<int, int>> get_anchors() const {
        vector<pair<int, int>> anchors;
        bool is_empty = true;

        for (int r = 0; r < 15; r++) {
            for (int c = 0; c < 15; c++) {
                if (grid[r][c] != 0) {
                    is_empty = false;
                    break;
                }
            }
            if (!is_empty) break;
        }

        if (is_empty) {
            anchors.push_back({7, 7});
            return anchors;
        }

        for (int r = 0; r < 15; r++) {
            for (int c = 0; c < 15; c++) {
                if (grid[r][c] == 0) {
                    bool adj = false;
                    int nr, nc;
                    int dr[] = {-1, 1, 0, 0};
                    int dc[] = {0, 0, -1, 1};
                    for (int i = 0; i < 4; i++) {
                        nr = r + dr[i];
                        nc = c + dc[i];
                        if (nr >= 0 && nr < 15 && nc >= 0 && nc < 15) {
                            if (grid[nr][nc] != 0) {
                                adj = true;
                                break;
                            }
                        }
                    }
                    if (adj) {
                        anchors.push_back({r, c});
                    }
                }
            }
        }
        return anchors;
    }

    BoardState transpose() const {
        BoardState t;
        for (int r = 0; r < 15; r++) {
            for (int c = 0; c < 15; c++) {
                t.grid[c][r] = grid[r][c];
                t.blank_grid[c][r] = blank_grid[r][c];
            }
        }
        return t;
    }
};

// Represents a placed tile in move search
struct PlacedTile {
    int r;
    int c;
    char letter;
    bool is_blank;
};

struct Move {
    string word;
    int r;
    int c;
    char direction; // 'H' or 'V'
    vector<PlacedTile> tiles_placed;
};

// Standard types
using CrossChecks = unordered_map<int, uint32_t>; // bitmask of valid chars A-Z (bits 0-25)

uint32_t ALL_LETTERS_MASK = 0x3FFFFFF; // first 26 bits set

CrossChecks compute_vertical_cross_checks(const BoardState& board, const GADDAG& gaddag) {
    CrossChecks cc;
    for (int r = 0; r < 15; r++) {
        for (int c = 0; c < 15; c++) {
            if (board.get_tile(r, c) != 0) continue;

            // Scan up
            string up_str = "";
            int curr_r = r - 1;
            while (curr_r >= 0 && board.get_tile(curr_r, c) != 0) {
                up_str += board.get_tile(curr_r, c);
                curr_r--;
            }
            reverse(up_str.begin(), up_str.end());

            // Scan down
            string down_str = "";
            curr_r = r + 1;
            while (curr_r < 15 && board.get_tile(curr_r, c) != 0) {
                down_str += board.get_tile(curr_r, c);
                curr_r++;
            }

            if (up_str.empty() && down_str.empty()) {
                cc[r * 15 + c] = ALL_LETTERS_MASK;
            } else {
                uint32_t mask = 0;
                for (int i = 0; i < 26; i++) {
                    char char_candidate = 'A' + i;
                    string word = up_str + char_candidate + down_str;
                    if (gaddag.contains(word)) {
                        mask |= (1 << i);
                    }
                }
                cc[r * 15 + c] = mask;
            }
        }
    }
    return cc;
}

class MoveScorer {
public:
    static int score_move(const BoardState& board, const Move& move) {
        // Fast map of placed tiles
        char placed_letters[15][15] = {0};
        bool is_blank_tile[15][15] = {false};
        for (const auto& tp : move.tiles_placed) {
            placed_letters[tp.r][tp.c] = tp.letter;
            is_blank_tile[tp.r][tp.c] = tp.is_blank;
        }

        auto score_word_segment = [&](int start_r, int start_c, int end_r, int end_c, char direction) -> int {
            int total = 0;
            int word_mult = 1;
            int curr_r = start_r;
            int curr_c = start_c;

            while (true) {
                char existing = board.get_tile(curr_r, curr_c);
                if (existing != 0) {
                    total += board.is_blank(curr_r, curr_c) ? 0 : get_letter_value(existing);
                } else {
                    char c = placed_letters[curr_r][curr_c];
                    int val = is_blank_tile[curr_r][curr_c] ? 0 : get_letter_value(c);
                    string mult = BOARD_MULTIPLIERS[curr_r][curr_c];

                    if (mult == "DL") total += val * 2;
                    else if (mult == "TL") total += val * 3;
                    else if (mult == "DW") { total += val; word_mult *= 2; }
                    else if (mult == "TW") { total += val; word_mult *= 3; }
                    else total += val;
                }

                if (direction == 'H') {
                    if (curr_c == end_c) break;
                    curr_c++;
                } else {
                    if (curr_r == end_r) break;
                    curr_r++;
                }
            }
            return total * word_mult;
        };

        int total_score = 0;

        // 1. Score primary word
        if (move.direction == 'H') {
            int r = move.r;
            int start_c = move.c;
            int end_c = start_c;
            while (end_c < 14 && (board.get_tile(r, end_c + 1) != 0 || placed_letters[r][end_c + 1] != 0)) {
                end_c++;
            }
            total_score += score_word_segment(r, start_c, r, end_c, 'H');
        } else {
            int c = move.c;
            int start_r = move.r;
            int end_r = start_r;
            while (end_r < 14 && (board.get_tile(end_r + 1, c) != 0 || placed_letters[end_r + 1][c] != 0)) {
                end_r++;
            }
            total_score += score_word_segment(start_r, c, end_r, c, 'V');
        }

        // 2. Score perpendicular cross-words
        for (const auto& tp : move.tiles_placed) {
            int tr = tp.r;
            int tc = tp.c;
            if (move.direction == 'H') {
                vector<int> up_idx;
                int curr_r = tr - 1;
                while (curr_r >= 0 && board.get_tile(curr_r, tc) != 0) {
                    up_idx.push_back(curr_r);
                    curr_r--;
                }
                vector<int> down_idx;
                curr_r = tr + 1;
                while (curr_r < 15 && board.get_tile(curr_r, tc) != 0) {
                    down_idx.push_back(curr_r);
                    curr_r++;
                }

                if (!up_idx.empty() || !down_idx.empty()) {
                    int start_r = up_idx.empty() ? tr : *min_element(up_idx.begin(), up_idx.end());
                    int end_r = down_idx.empty() ? tr : *max_element(down_idx.begin(), down_idx.end());
                    total_score += score_word_segment(start_r, tc, end_r, tc, 'V');
                }
            } else {
                vector<int> left_idx;
                int curr_c = tc - 1;
                while (curr_c >= 0 && board.get_tile(tr, curr_c) != 0) {
                    left_idx.push_back(curr_c);
                    curr_c--;
                }
                vector<int> right_idx;
                curr_c = tc + 1;
                while (curr_c < 15 && board.get_tile(tr, curr_c) != 0) {
                    right_idx.push_back(curr_c);
                    curr_c++;
                }

                if (!left_idx.empty() || !right_idx.empty()) {
                    int start_c = left_idx.empty() ? tc : *min_element(left_idx.begin(), left_idx.end());
                    int end_c = right_idx.empty() ? tc : *max_element(right_idx.begin(), right_idx.end());
                    total_score += score_word_segment(tr, start_c, tr, end_c, 'H');
                }
            }
        }

        // 3. Bingo Bonus
        if (move.tiles_placed.size() == 7) {
            total_score += 50;
        }

        return total_score;
    }

    static double evaluate_move(const BoardState& board, const Move& move, const vector<char>& original_rack) {
        double score = score_move(board, move);

        // Rack leave
        unordered_multiset<char> remaining_rack(original_rack.begin(), original_rack.end());
        for (const auto& tp : move.tiles_placed) {
            char ref_letter = tp.is_blank ? '?' : tp.letter;
            auto it = remaining_rack.find(ref_letter);
            if (it != remaining_rack.end()) {
                remaining_rack.erase(it);
            }
        }

        double rack_equity = 0.0;
        int vowels_count = 0;
        int consonants_count = 0;
        unordered_map<char, int> counts;

        for (char ch : remaining_rack) {
            auto it = RACK_LEAVE_EQUITIES.find(ch);
            if (it != RACK_LEAVE_EQUITIES.end()) {
                rack_equity += it->second;
            }
            if (ch == 'A' || ch == 'E' || ch == 'I' || ch == 'O' || ch == 'U') {
                vowels_count++;
            } else if (ch != '?') {
                consonants_count++;
            }
            counts[ch]++;
        }

        // Vowel consonant balance
        if (!remaining_rack.empty()) {
            if (vowels_count == 3 && consonants_count == 4) rack_equity += 3.0;
            else if (vowels_count == 4 && consonants_count == 3) rack_equity += 3.0;
            else if (vowels_count == 0 || consonants_count == 0) rack_equity -= 10.0;
            else if (vowels_count == 1 || consonants_count == 1) rack_equity -= 4.0;
            else if (vowels_count >= 5 || consonants_count >= 5) rack_equity -= 5.0;
        }

        // Duplicates
        for (const auto& pair : counts) {
            if (pair.second > 1 && pair.first != '?') {
                rack_equity -= 2.5 * (pair.second - 1);
            }
        }

        // Defensive penalties
        double defense_penalty = 0.0;
        int dr[] = {-1, 1, 0, 0};
        int dc[] = {0, 0, -1, 1};

        for (const auto& tp : move.tiles_placed) {
            for (int i = 0; i < 4; i++) {
                int nr = tp.r + dr[i];
                int nc = tp.c + dc[i];
                if (nr >= 0 && nr < 15 && nc >= 0 && nc < 15) {
                    if (board.get_tile(nr, nc) == 0) {
                        string mult = BOARD_MULTIPLIERS[nr][nc];
                        if (mult == "TW") defense_penalty += 12.0;
                        else if (mult == "DW") defense_penalty += 6.0;
                        else if (mult == "TL") defense_penalty += 4.0;
                    }
                }
            }
        }

        return score + rack_equity - defense_penalty;
    }
};

class MoveGenerator {
private:
    const GADDAG& gaddag;

    void search_left(
        const BoardState& board, int r, int anchor_c, int curr_c,
        int node_idx, unordered_map<char, int>& rack_counts,
        vector<PlacedTile>& tiles_placed, const CrossChecks& cc,
        vector<Move>& moves, char direction
    ) {
        int next_c = curr_c - 1;

        if (next_c >= 0) {
            char tile = board.get_tile(r, next_c);
            if (tile != 0) {
                int child = gaddag.get_child(node_idx, tile);
                if (child != -1) {
                    search_left(board, r, anchor_c, next_c, child, rack_counts, tiles_placed, cc, moves, direction);
                }
            } else {
                // Flip right
                int flip_child = gaddag.get_child(node_idx, FLIP_RIGHT);
                if (flip_child != -1) {
                    search_right(board, r, anchor_c, anchor_c, flip_child, rack_counts, tiles_placed, cc, moves, direction);
                }

                // Place tile from rack
                for (auto& pair : rack_counts) {
                    if (pair.second <= 0) continue;
                    char letter = pair.first;

                    if (letter == '?') {
                        // Try placing all characters
                        for (int i = 0; i < 26; i++) {
                            char char_candidate = 'A' + i;
                            int child = gaddag.get_child(node_idx, char_candidate);
                            if (child != -1) {
                                uint32_t cell_mask = cc.at(r * 15 + next_c);
                                if (cell_mask & (1 << i)) {
                                    pair.second--;
                                    tiles_placed.push_back({r, next_c, char_candidate, true});
                                    search_left(board, r, anchor_c, next_c, child, rack_counts, tiles_placed, cc, moves, direction);
                                    tiles_placed.pop_back();
                                    pair.second++;
                                }
                            }
                        }
                    } else {
                        int child = gaddag.get_child(node_idx, letter);
                        if (child != -1) {
                            uint32_t cell_mask = cc.at(r * 15 + next_c);
                            int char_idx = letter - 'A';
                            if (cell_mask & (1 << char_idx)) {
                                pair.second--;
                                tiles_placed.push_back({r, next_c, letter, false});
                                search_left(board, r, anchor_c, next_c, child, rack_counts, tiles_placed, cc, moves, direction);
                                tiles_placed.pop_back();
                                pair.second++;
                            }
                        }
                    }
                }
            }
        } else {
            // Hit boundary, only flip right
            int flip_child = gaddag.get_child(node_idx, FLIP_RIGHT);
            if (flip_child != -1) {
                search_right(board, r, anchor_c, anchor_c, flip_child, rack_counts, tiles_placed, cc, moves, direction);
            }
        }
    }

    void search_right(
        const BoardState& board, int r, int anchor_c, int curr_c,
        int node_idx, unordered_map<char, int>& rack_counts,
        vector<PlacedTile>& tiles_placed, const CrossChecks& cc,
        vector<Move>& moves, char direction
    ) {
        int next_c = curr_c + 1;

        // 1. Is it a word terminal?
        if (gaddag.get_child(node_idx, WORD_END) != -1) {
            if (!tiles_placed.empty()) {
                if (next_c >= 15 || board.get_tile(r, next_c) == 0) {
                    // Reconstruct
                    int start_c = anchor_c;
                    auto is_tile_or_placed = [&](int tc) {
                        if (board.get_tile(r, tc) != 0) return true;
                        for (const auto& tp : tiles_placed) if (tp.c == tc) return true;
                        return false;
                    };
                    while (start_c > 0 && is_tile_or_placed(start_c - 1)) {
                        start_c--;
                    }
                    int end_c = anchor_c;
                    while (end_c < 14 && is_tile_or_placed(end_c + 1)) {
                        end_c++;
                    }

                    string full_word = "";
                    for (int tc = start_c; tc <= end_c; tc++) {
                        char existing = board.get_tile(r, tc);
                        if (existing != 0) {
                            full_word += existing;
                        } else {
                            for (const auto& tp : tiles_placed) {
                                if (tp.c == tc) {
                                    full_word += tp.letter;
                                    break;
                                }
                            }
                        }
                    }
                    moves.push_back({full_word, r, start_c, direction, tiles_placed});
                }
            }
        }

        // 2. Traverse further right
        if (next_c < 15) {
            char tile = board.get_tile(r, next_c);
            if (tile != 0) {
                int child = gaddag.get_child(node_idx, tile);
                if (child != -1) {
                    search_right(board, r, anchor_c, next_c, child, rack_counts, tiles_placed, cc, moves, direction);
                }
            } else {
                for (auto& pair : rack_counts) {
                    if (pair.second <= 0) continue;
                    char letter = pair.first;

                    if (letter == '?') {
                        for (int i = 0; i < 26; i++) {
                            char char_candidate = 'A' + i;
                            int child = gaddag.get_child(node_idx, char_candidate);
                            if (child != -1) {
                                uint32_t cell_mask = cc.at(r * 15 + next_c);
                                if (cell_mask & (1 << i)) {
                                    pair.second--;
                                    tiles_placed.push_back({r, next_c, char_candidate, true});
                                    search_right(board, r, anchor_c, next_c, child, rack_counts, tiles_placed, cc, moves, direction);
                                    tiles_placed.pop_back();
                                    pair.second++;
                                }
                            }
                        }
                    } else {
                        int child = gaddag.get_child(node_idx, letter);
                        if (child != -1) {
                            uint32_t cell_mask = cc.at(r * 15 + next_c);
                            int char_idx = letter - 'A';
                            if (cell_mask & (1 << char_idx)) {
                                pair.second--;
                                tiles_placed.push_back({r, next_c, letter, false});
                                search_right(board, r, anchor_c, next_c, child, rack_counts, tiles_placed, cc, moves, direction);
                                tiles_placed.pop_back();
                                pair.second++;
                            }
                        }
                    }
                }
            }
        }
    }

public:
    MoveGenerator(const GADDAG& gaddag_ref) : gaddag(gaddag_ref) {}

    vector<Move> generate_all_moves(const BoardState& board, const vector<char>& rack) {
        unordered_map<char, int> rack_counts;
        for (char c : rack) rack_counts[toupper(c)]++;

        // 1. Generate Horizontal
        vector<Move> horizontal_moves;
        auto anchors = board.get_anchors();
        auto cc = compute_vertical_cross_checks(board, gaddag);

        for (const auto& anchor : anchors) {
            int anchor_r = anchor.first;
            int anchor_c = anchor.second;

            for (auto& pair : rack_counts) {
                if (pair.second <= 0) continue;
                char letter = pair.first;

                if (letter == '?') {
                    for (int i = 0; i < 26; i++) {
                        char char_candidate = 'A' + i;
                        int child = gaddag.get_child(0, char_candidate);
                        if (child != -1) {
                            uint32_t cell_mask = cc[anchor_r * 15 + anchor_c];
                            if (cell_mask & (1 << i)) {
                                pair.second--;
                                vector<PlacedTile> tp = {{anchor_r, anchor_c, char_candidate, true}};
                                search_left(board, anchor_r, anchor_c, anchor_c, child, rack_counts, tp, cc, horizontal_moves, 'H');
                                pair.second++;
                            }
                        }
                    }
                } else {
                    int child = gaddag.get_child(0, letter);
                    if (child != -1) {
                        uint32_t cell_mask = cc[anchor_r * 15 + anchor_c];
                        int char_idx = letter - 'A';
                        if (cell_mask & (1 << char_idx)) {
                            pair.second--;
                            vector<PlacedTile> tp = {{anchor_r, anchor_c, letter, false}};
                            search_left(board, anchor_r, anchor_c, anchor_c, child, rack_counts, tp, cc, horizontal_moves, 'H');
                            pair.second++;
                        }
                    }
                }
            }
        }

        // 2. Generate Vertical via Transposing
        BoardState transposed_board = board.transpose();
        vector<Move> transposed_moves;
        auto t_anchors = transposed_board.get_anchors();
        auto t_cc = compute_vertical_cross_checks(transposed_board, gaddag);

        for (const auto& anchor : t_anchors) {
            int anchor_r = anchor.first;
            int anchor_c = anchor.second;

            for (auto& pair : rack_counts) {
                if (pair.second <= 0) continue;
                char letter = pair.first;

                if (letter == '?') {
                    for (int i = 0; i < 26; i++) {
                        char char_candidate = 'A' + i;
                        int child = gaddag.get_child(0, char_candidate);
                        if (child != -1) {
                            uint32_t cell_mask = t_cc[anchor_r * 15 + anchor_c];
                            if (cell_mask & (1 << i)) {
                                pair.second--;
                                vector<PlacedTile> tp = {{anchor_r, anchor_c, char_candidate, true}};
                                search_left(transposed_board, anchor_r, anchor_c, anchor_c, child, rack_counts, tp, t_cc, transposed_moves, 'V');
                                pair.second++;
                            }
                        }
                    }
                } else {
                    int child = gaddag.get_child(0, letter);
                    if (child != -1) {
                        uint32_t cell_mask = t_cc[anchor_r * 15 + anchor_c];
                        int char_idx = letter - 'A';
                        if (cell_mask & (1 << char_idx)) {
                            pair.second--;
                            vector<PlacedTile> tp = {{anchor_r, anchor_c, letter, false}};
                            search_left(transposed_board, anchor_r, anchor_c, anchor_c, child, rack_counts, tp, t_cc, transposed_moves, 'V');
                            pair.second++;
                        }
                    }
                }
            }
        }

        // Transform transposed vertical moves back to V format
        vector<Move> vertical_moves;
        for (const auto& m : transposed_moves) {
            int orig_r = m.c;
            int orig_c = m.r;
            vector<PlacedTile> orig_tp;
            for (const auto& tp : m.tiles_placed) {
                orig_tp.push_back({tp.c, tp.r, tp.letter, tp.is_blank});
            }
            vertical_moves.push_back({m.word, orig_r, orig_c, 'V', orig_tp});
        }

        vector<Move> all_moves = horizontal_moves;
        all_moves.insert(all_moves.end(), vertical_moves.begin(), vertical_moves.end());
        return all_moves;
    }
};

class MonteCarloSolver {
private:
    MoveGenerator& generator;

public:
    MonteCarloSolver(MoveGenerator& gen) : generator(gen) {}

    pair<Move, double> select_best_move_mc(
        const BoardState& board, const vector<char>& rack,
        vector<char>& unseen_bag, int top_k = 5, int num_simulations = 5
    ) {
        auto all_moves = generator.generate_all_moves(board, rack);
        if (all_moves.empty()) {
            return {Move(), -9999.0};
        }

        // Score them and sort
        vector<pair<Move, double>> scored_moves;
        for (const auto& m : all_moves) {
            double util = MoveScorer::evaluate_move(board, m, rack);
            scored_moves.push_back({m, util});
        }

        auto move_key = [](const Move& move) {
            string key = move.word + "|" + to_string(move.r) + "|" + to_string(move.c) + "|" + move.direction;
            vector<PlacedTile> tiles = move.tiles_placed;
            sort(tiles.begin(), tiles.end(), [](const PlacedTile& a, const PlacedTile& b) {
                if (a.r != b.r) return a.r < b.r;
                if (a.c != b.c) return a.c < b.c;
                if (a.letter != b.letter) return a.letter < b.letter;
                return a.is_blank < b.is_blank;
            });
            for (const auto& tile : tiles) {
                key += "|" + to_string(tile.r) + "," + to_string(tile.c) + "," + tile.letter + (tile.is_blank ? "B" : "T");
            }
            return key;
        };
        sort(scored_moves.begin(), scored_moves.end(), [&](const auto& a, const auto& b) {
            if (a.second != b.second) return a.second > b.second;
            return move_key(a.first) < move_key(b.first);
        });

        int limit = min((int)scored_moves.size(), top_k);
        Move best_move;
        double best_ev = -9999.0;

        // Stable FNV-1a seed: identical game states produce identical rollouts and EVs.
        uint32_t seed = 2166136261u;
        auto mix = [&](uint8_t value) {
            seed ^= value;
            seed *= 16777619u;
        };
        for (int r = 0; r < 15; r++) {
            for (int c = 0; c < 15; c++) {
                mix(static_cast<uint8_t>(board.get_tile(r, c)));
                mix(board.is_blank(r, c) ? 1 : 0);
            }
        }
        vector<char> canonical_rack = rack;
        vector<char> canonical_bag = unseen_bag;
        sort(canonical_rack.begin(), canonical_rack.end());
        sort(canonical_bag.begin(), canonical_bag.end());
        for (char ch : canonical_rack) mix(static_cast<uint8_t>(ch));
        mix(0xFF);
        for (char ch : canonical_bag) mix(static_cast<uint8_t>(ch));

        for (int i = 0; i < limit; i++) {
            const auto& move = scored_moves[i].first;
            double total_score_diff = 0.0;
            mt19937 rng(seed ^ (0x9E3779B9u * static_cast<uint32_t>(i + 1)));

            // Apply play temporarily
            BoardState sim_board = board;
            for (const auto& tp : move.tiles_placed) {
                sim_board.set_tile(tp.r, tp.c, tp.letter, tp.is_blank);
            }

            // The rack has already been drawn from unseen_bag by the frontend.
            // Playing rack tiles therefore does not remove matching tiles from the bag.
            vector<char> bag_after_play = canonical_bag;

            int our_score = MoveScorer::score_move(board, move);

            for (int sim = 0; sim < num_simulations; sim++) {
                if (bag_after_play.empty()) {
                    total_score_diff += our_score;
                    continue;
                }

                // Draw opponent rack
                vector<char> sampled_bag = bag_after_play;
                shuffle(sampled_bag.begin(), sampled_bag.end(), rng);
                int draw_size = min(7, (int)sampled_bag.size());
                vector<char> opp_rack(sampled_bag.begin(), sampled_bag.begin() + draw_size);

                // Find opponent plays
                auto opp_moves = generator.generate_all_moves(sim_board, opp_rack);
                int opp_best_score = 0;
                if (!opp_moves.empty()) {
                    for (const auto& op_m : opp_moves) {
                        opp_best_score = max(opp_best_score, MoveScorer::score_move(sim_board, op_m));
                    }
                }
                total_score_diff += (our_score - opp_best_score);
            }

            double avg_ev = total_score_diff / num_simulations;

            // Factor in a small weight of the rack leave utility
            unordered_multiset<char> remaining_rack(rack.begin(), rack.end());
            for (const auto& tp : move.tiles_placed) {
                char ref = tp.is_blank ? '?' : tp.letter;
                auto it = remaining_rack.find(ref);
                if (it != remaining_rack.end()) remaining_rack.erase(it);
            }
            double rack_leave = 0.0;
            for (char ch : remaining_rack) {
                auto it = RACK_LEAVE_EQUITIES.find(ch);
                if (it != RACK_LEAVE_EQUITIES.end()) rack_leave += it->second;
            }

            double composite_ev = avg_ev + 0.5 * rack_leave + 0.1 * our_score;

            if (composite_ev > best_ev) {
                best_ev = composite_ev;
                best_move = move;
            }
        }

        return {best_move, best_ev};
    }
};

// Extremely simple hand-rolled JSON parser to read stdin cleanly without external deps
struct ParsedInput {
    BoardState board;
    vector<char> rack;
    vector<char> bag;
};

ParsedInput parse_simple_json(const string& full_input) {
    ParsedInput input;

    // Helper to find strings in json
    auto extract_array_of_chars = [&](const string& key) -> vector<char> {
        vector<char> result;
        size_t key_pos = full_input.find("\"" + key + "\"");
        if (key_pos == string::npos) return result;
        size_t start_bracket = full_input.find("[", key_pos);
        if (start_bracket == string::npos) return result;
        size_t end_bracket = full_input.find("]", start_bracket);
        if (end_bracket == string::npos) return result;

        string contents = full_input.substr(start_bracket + 1, end_bracket - start_bracket - 1);
        stringstream ss(contents);
        string item;
        while (getline(ss, item, ',')) {
            // Trim quotes and whitespace
            size_t q1 = item.find("\"");
            if (q1 != string::npos) {
                size_t q2 = item.find("\"", q1 + 1);
                if (q2 != string::npos) {
                    string s = item.substr(q1 + 1, q2 - q1 - 1);
                    if (!s.empty()) result.push_back(s[0]);
                }
            } else {
                // Check if single characters without quotes
                for (char c : item) {
                    if (isalpha(c) || c == '?') {
                        result.push_back(c);
                        break;
                    }
                }
            }
        }
        return result;
    };

    input.rack = extract_array_of_chars("rack");
    input.bag = extract_array_of_chars("bag");

    // Extract board - 15x15 of Square: {letter: "A" | null}
    size_t board_pos = full_input.find("\"board\"");
    if (board_pos != string::npos) {
        size_t grid_start = full_input.find("[", board_pos);
        int r = 0, c = 0;
        size_t pos = grid_start;
        while (r < 15 && pos < full_input.length()) {
            size_t cell_start = full_input.find("{", pos);
            if (cell_start == string::npos) break;
            size_t cell_end = full_input.find("}", cell_start);
            if (cell_end == string::npos) break;

            string cell_str = full_input.substr(cell_start, cell_end - cell_start);
            size_t let_key = cell_str.find("\"letter\"");
            if (let_key != string::npos) {
                size_t colon = cell_str.find(":", let_key);
                if (colon != string::npos) {
                    size_t first_char = cell_str.find_first_not_of(" \t\r\n", colon + 1);
                    if (first_char != string::npos && cell_str[first_char] == '\"') {
                        char letter_val = cell_str[first_char + 1];
                        if (letter_val != '\"') {
                            bool is_blank = false;
                            size_t blank_key = cell_str.find("\"isBlank\"");
                            if (blank_key != string::npos) {
                                size_t blank_colon = cell_str.find(":", blank_key);
                                size_t blank_value = cell_str.find_first_not_of(" \t\r\n", blank_colon + 1);
                                is_blank = blank_value != string::npos && cell_str.compare(blank_value, 4, "true") == 0;
                            }
                            input.board.set_tile(r, c, letter_val, is_blank);
                        }
                    }
                }
            }

            c++;
            if (c >= 15) {
                c = 0;
                r++;
            }
            pos = cell_end;
        }
    }

    return input;
}

int main() {
    // Load the dictionary once, then serve newline-delimited JSON requests until stdin closes.
    GADDAG gaddag;
    gaddag.load_dictionary("words.txt");
    MoveGenerator generator(gaddag);
    MonteCarloSolver solver(generator);

    string request_json;
    while (getline(cin, request_json)) {
        if (request_json.empty()) continue;

        ParsedInput input = parse_simple_json(request_json);
        auto result = solver.select_best_move_mc(input.board, input.rack, input.bag, 5, 5);
        Move best_move = result.first;
        double ev = result.second;

        ostringstream response;
        if (!best_move.word.empty()) {
            int score = MoveScorer::score_move(input.board, best_move);
            response << "{\"success\":true,\"word\":\"" << best_move.word
                     << "\",\"r\":" << best_move.r
                     << ",\"c\":" << best_move.c
                     << ",\"direction\":\"" << best_move.direction
                     << "\",\"score\":" << score
                     << ",\"ev\":" << round(ev * 100.0) / 100.0
                     << ",\"tilesPlaced\":[";
            for (size_t i = 0; i < best_move.tiles_placed.size(); i++) {
                const auto& tp = best_move.tiles_placed[i];
                if (i > 0) response << ",";
                response << "{\"r\":" << tp.r
                         << ",\"c\":" << tp.c
                         << ",\"letter\":\"" << tp.letter
                         << "\",\"isBlank\":" << (tp.is_blank ? "true" : "false") << "}";
            }
            response << "]}";
        } else {
            response << "{\"success\":false,\"word\":\"PASS\",\"tilesPlaced\":[]}";
        }
        cout << response.str() << '\n' << flush;
    }

    return 0;
}
