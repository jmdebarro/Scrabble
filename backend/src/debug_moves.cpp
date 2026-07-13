#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <unordered_map>
#include <algorithm>
#include <sstream>

// Preprocessor trick to rename main in main.cpp so we can write our own main here
#define main main_disabled
#include "main.cpp"
#undef main

int main() {
    cout << "=== Debugging GADDAG Move Generation ===" << endl;
    
    // 1. Load GADDAG
    GADDAG gaddag;
    gaddag.load_dictionary("words.txt");
    cout << "GADDAG loaded. Nodes size: " << gaddag.nodes.size() << endl;
    
    // Check if some basic words are in GADDAG
    cout << "Contains 'CAT'? " << gaddag.contains("CAT") << endl;
    cout << "Contains 'ACT'? " << gaddag.contains("ACT") << endl;
    cout << "Contains 'COAT'? " << gaddag.contains("COAT") << endl;

    // 2. Setup board
    BoardState board;
    board.set_tile(7, 7, 'C');
    
    // 3. Setup rack
    vector<char> rack = {'A', 'T', 'O', 'X', 'E', 'O', 'O'};
    
    // 4. Generate moves
    MoveGenerator generator(gaddag);
    auto moves = generator.generate_all_moves(board, rack);
    
    cout << "\nGenerated " << moves.size() << " moves:" << endl;
    for (size_t i = 0; i < min((size_t)20, moves.size()); i++) {
        const auto& m = moves[i];
        cout << "Move " << i << ": word=" << m.word << ", start=(" << m.r << "," << m.c << "), dir=" << m.direction << ", score=" << MoveScorer::score_move(board, m) << ", utility=" << MoveScorer::evaluate_move(board, m, rack) << endl;
    }
    
    return 0;
}
