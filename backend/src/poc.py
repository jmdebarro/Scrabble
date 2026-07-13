from __future__ import annotations
import os

# 1. Trie/GADDAG dictionary
# 2. Appel/Jacobson move generation
# 3. Rack leave table
# 4. Monte Carlo rollout evaluation

FILE = "words.txt"
FLIP_RIGHT = "<"

class GADDAG:
    """GADDAG structure contains every word in every variation, using nested dictionaries"""

    def __init__(self):
        self.root = {}

    def insert_variation(self, variation: str):
        # Insert word variation into the GADDAG tree
        cur_node = self.root
        for char in variation:
            if char not in cur_node:
                cur_node[char] = {}
            cur_node = cur_node[char]

    def create_gaddag(self):
        # Create GADDAG tree from words.txt file
        if not os.path.exists(FILE):
            # Try to look for it relative to current file if run directly
            local_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), FILE)
            if os.path.exists(local_file):
                path = local_file
            else:
                print(f"Warning: {FILE} not found.")
                return
        else:
            path = FILE

        with open(path, "r") as file:
            for line in file:
                word = line.strip().upper()
                if not word:
                    continue
                # Create word variations
                word_variations = self._create_word_graphs(word)

                # Insert every variation into the GADDAG
                for variation in word_variations:
                    self.insert_variation(variation)

    @staticmethod
    def _create_word_graphs(s: str) -> list[str]:
        # Creates every variation of a word
        word_variations = []
        cur_word_iteration = ""
        length = len(s)
        for i in range(length):
            # attach anchor letter to beginning
            cur_word_iteration += s[i]
            prev = i - 1
            while prev >= 0:
                cur_word_iteration += s[prev]
                prev -= 1
            if i <= length - 1:
                cur_word_iteration += FLIP_RIGHT
                cur_word_iteration += s[i+1:]

            word_variations.append(cur_word_iteration)
            cur_word_iteration = ""

        return word_variations

    def _format_tree(self, node: dict, prefix: str = "") -> str:
        lines = []
        keys = sorted(node.keys())
        for i, key in enumerate(keys):
            is_last = (i == len(keys) - 1)
            connector = "└── " if is_last else "├── "
            val = node[key]
            if not val:
                lines.append(f"{prefix}{connector}{key}")
            else:
                lines.append(f"{prefix}{connector}{key}")
                next_prefix = prefix + ("    " if is_last else "│   ")
                lines.append(self._format_tree(val, next_prefix))
        return "\n".join(lines)

    def __str__(self) -> str:
        if not self.root:
            return "Empty GADDAG"
        return self._format_tree(self.root)

    def __repr__(self) -> str:
        return f"GADDAG({repr(self.root)})"