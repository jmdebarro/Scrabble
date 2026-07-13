#include <iostream>
#include <string>
#include <vector>
#include <unordered_map>
#include <sstream>
#include <algorithm>

using namespace std;

struct BoardState {
    char grid[15][15];
    BoardState() {
        for (int r = 0; r < 15; r++) {
            for (int c = 0; c < 15; c++) {
                grid[r][c] = 0;
            }
        }
    }
    void set_tile(int r, int c, char letter) {
        if (r >= 0 && r < 15 && c >= 0 && c < 15) {
            grid[r][c] = toupper(letter);
        }
    }
};

struct ParsedInput {
    BoardState board;
    vector<char> rack;
    vector<char> bag;
};

ParsedInput parse_simple_json_stdin(const string& full_input) {
    ParsedInput input;

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
            size_t q1 = item.find("\"");
            if (q1 != string::npos) {
                size_t q2 = item.find("\"", q1 + 1);
                if (q2 != string::npos) {
                    string s = item.substr(q1 + 1, q2 - q1 - 1);
                    if (!s.empty()) result.push_back(s[0]);
                }
            } else {
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
                            input.board.set_tile(r, c, letter_val);
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
    // Construct mock input string exactly like urllib sends
    string mock_json = "{\"board\": [";
    for (int r = 0; r < 15; r++) {
        mock_json += "[";
        for (int c = 0; c < 15; c++) {
            if (r == 7 && c == 7) {
                mock_json += "{\"letter\": \"C\", \"multiplier\": \"double_word\"}";
            } else {
                mock_json += "{\"letter\": null, \"multiplier\": \"none\"}";
            }
            if (c < 14) mock_json += ", ";
        }
        mock_json += "]";
        if (r < 14) mock_json += ", ";
    }
    mock_json += "], \"rack\": [\"A\", \"T\", \"O\", \"X\", \"E\", \"O\", \"O\"], \"bag\": [\"A\"]}";

    ParsedInput input = parse_simple_json_stdin(mock_json);

    cout << "Rack parsed: ";
    for (char ch : input.rack) cout << ch << " ";
    cout << endl;

    cout << "Board parsed tiles:" << endl;
    int tile_count = 0;
    for (int r = 0; r < 15; r++) {
        for (int c = 0; c < 15; c++) {
            if (input.board.grid[r][c] != 0) {
                cout << "Tile at (" << r << "," << c << "): '" << input.board.grid[r][c] << "'" << endl;
                tile_count++;
            }
        }
    }
    cout << "Total tiles found on board: " << tile_count << endl;

    return 0;
}
