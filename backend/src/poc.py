from __future__ import annotations

# 1. Trie/GADDAG dictionary
# 2. Appel/Jacobson move generation
# 3. Rack leave table
# 4. Monte Carlo rollout evaluation

FILE = "words.txt"

class Node:
    """Tree node for GADDAG structure"""

    def __init__(self, value: str):
        self.value = value
        self.next = {}


    def __eq__(self, other) -> bool:
        if isinstance(other, Node):
            return other.value == self.value
        return False


    def add_node_to_next(self, next_node: Node):
        if next_node.value not in self.next:
            self.next[next_node.value] = next_node


    def find_next(self, node: Node):
        if node in self.next:
            return self.next



class GADDAG:
    """GADDAG structure contains every word in every variation"""

    def __init__(self):
        self.gaddag = self.create_gaddag()

    def create_gaddag(self):
