export enum Multiplier {
  double_letter = "double_letter",
  triple_letter = "triple_letter",
  double_word = "double_word",
  triple_word = "triple_word",
  none = "none"
}

export type Square = {
  multiplier: Multiplier;
  letter: string | null;
  isLocked?: boolean;
};

export interface PlacedTile {
  r: number;
  c: number;
  letter: string;
}

export interface MoveResult {
  success: boolean;
  error?: string;
  score?: number;
  words?: string[];
}

export const LETTER_VALUES: Record<string, number> = {
  A: 1, B: 3, C: 3, D: 2, E: 1, F: 4, G: 2, H: 4, I: 1, J: 8, K: 5, L: 1, M: 3,
  N: 1, O: 1, P: 3, Q: 10, R: 1, S: 1, T: 1, U: 1, V: 4, W: 4, X: 8, Y: 4, Z: 10
};

const T = Multiplier.triple_word;
const D = Multiplier.double_word;
const TL = Multiplier.triple_letter;
const DL = Multiplier.double_letter;
const N = Multiplier.none;

const BOARD_LAYOUT: Multiplier[][] = [
  [T,  N,  N,  DL, N,  N,  N,  T,  N,  N,  N,  DL, N,  N,  T],
  [N,  D,  N,  N,  N,  TL, N,  N,  N,  TL, N,  N,  N,  D,  N],
  [N,  N,  D,  N,  N,  N,  DL, N,  DL, N,  N,  N,  D,  N,  N],
  [DL, N,  N,  D,  N,  N,  N,  DL, N,  N,  N,  D,  N,  N,  DL],
  [N,  N,  N,  N,  D,  N,  N,  N,  N,  N,  D,  N,  N,  N,  N],
  [N,  TL, N,  N,  N,  TL, N,  N,  N,  TL, N,  N,  N,  TL, N],
  [N,  N,  DL, N,  N,  N,  DL, N,  DL, N,  N,  N,  DL, N,  N],
  [T,  N,  N,  DL, N,  N,  N,  D,  N,  N,  N,  DL, N,  N,  T],
  [N,  N,  DL, N,  N,  N,  DL, N,  DL, N,  N,  N,  DL, N,  N],
  [N,  TL, N,  N,  N,  TL, N,  N,  N,  TL, N,  N,  N,  TL, N],
  [N,  N,  N,  N,  D,  N,  N,  N,  N,  N,  D,  N,  N,  N,  N],
  [DL, N,  N,  D,  N,  N,  N,  DL, N,  N,  N,  D,  N,  N,  DL],
  [N,  N,  D,  N,  N,  N,  DL, N,  DL, N,  N,  N,  D,  N,  N],
  [N,  D,  N,  N,  N,  TL, N,  N,  N,  TL, N,  N,  N,  D,  N],
  [T,  N,  N,  DL, N,  N,  N,  T,  N,  N,  N,  DL, N,  N,  T],
];

export function createBoard(): Square[][] {
  return BOARD_LAYOUT.map(row =>
    row.map(multiplier => ({
      multiplier,
      letter: null,
      isLocked: false,
    }))
  );
}

export function createTileBag(): string[] {
  const distribution: Record<string, number> = {
    A: 9, B: 2, C: 2, D: 4, E: 12, F: 2, G: 3, H: 2, I: 9, J: 1, K: 1, L: 4, M: 2,
    N: 6, O: 8, P: 2, Q: 1, R: 6, S: 4, T: 6, U: 4, V: 2, W: 2, X: 1, Y: 2, Z: 1
  };
  const bag: string[] = [];
  for (const [letter, count] of Object.entries(distribution)) {
    for (let i = 0; i < count; i++) {
      bag.push(letter);
    }
  }
  
  // Shuffle bag
  for (let i = bag.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [bag[i], bag[j]] = [bag[j], bag[i]];
  }
  return bag;
}

export function validateAndScoreMove(
  board: Square[][],
  placedTiles: PlacedTile[]
): MoveResult {
  if (placedTiles.length === 0) {
    return { success: false, error: "No tiles placed." };
  }

  // 1. Check if all placed tiles are on a single row or column
  const rows = placedTiles.map(t => t.r);
  const cols = placedTiles.map(t => t.c);
  const isRow = rows.every(r => r === rows[0]);
  const isCol = cols.every(c => c === cols[0]);

  if (!isRow && !isCol) {
    return {
      success: false,
      error: "Tiles must be placed in a single straight line (row or column)."
    };
  }

  // Determine alignment
  const alignment: 'row' | 'col' = isRow ? 'row' : 'col';

  // 2. Check for connectivity among the placed tiles themselves (no gaps)
  if (alignment === 'row') {
    const r = rows[0];
    const minC = Math.min(...cols);
    const maxC = Math.max(...cols);
    for (let c = minC; c <= maxC; c++) {
      if (board[r][c].letter === null) {
        return {
          success: false,
          error: "There cannot be gaps in your word."
        };
      }
    }
  } else {
    const c = cols[0];
    const minR = Math.min(...rows);
    const maxR = Math.max(...rows);
    for (let r = minR; r <= maxR; r++) {
      if (board[r][c].letter === null) {
        return {
          success: false,
          error: "There cannot be gaps in your word."
        };
      }
    }
  }

  // 3. Connectivity with existing board tiles
  let isFirstMove = true;
  for (let r = 0; r < 15; r++) {
    for (let c = 0; c < 15; c++) {
      if (board[r][c].isLocked) {
        isFirstMove = false;
        break;
      }
    }
    if (!isFirstMove) break;
  }

  if (isFirstMove) {
    // One of the placed tiles must cover the center star (7, 7)
    const coversCenter = placedTiles.some(t => t.r === 7 && t.c === 7);
    if (!coversCenter) {
      return {
        success: false,
        error: "The first word must cover the center square (★)."
      };
    }
  } else {
    // Must be adjacent to at least one locked tile
    let isConnected = false;
    for (const tile of placedTiles) {
      const neighbors = [
        { r: tile.r - 1, c: tile.c },
        { r: tile.r + 1, c: tile.c },
        { r: tile.r, c: tile.c - 1 },
        { r: tile.r, c: tile.c + 1 }
      ];
      for (const n of neighbors) {
        if (n.r >= 0 && n.r < 15 && n.c >= 0 && n.c < 15) {
          if (board[n.r][n.c].isLocked) {
            isConnected = true;
            break;
          }
        }
      }
      if (isConnected) break;
    }

    if (!isConnected) {
      return {
        success: false,
        error: "Your word must connect to an existing word on the board."
      };
    }
  }

  // 4. Find all words formed
  const wordsFormed: { word: string; cells: { r: number; c: number }[] }[] = [];

  if (placedTiles.length === 1) {
    const tile = placedTiles[0];
    
    // Horizontal check
    let leftC = tile.c;
    while (leftC > 0 && board[tile.r][leftC - 1].letter !== null) {
      leftC--;
    }
    let rightC = tile.c;
    while (rightC < 14 && board[tile.r][rightC + 1].letter !== null) {
      rightC++;
    }
    if (leftC !== rightC) {
      const hCells: { r: number; c: number }[] = [];
      for (let c = leftC; c <= rightC; c++) {
        hCells.push({ r: tile.r, c });
      }
      const wordStr = hCells.map(cell => board[cell.r][cell.c].letter).join("");
      wordsFormed.push({ word: wordStr, cells: hCells });
    }

    // Vertical check
    let topR = tile.r;
    while (topR > 0 && board[topR - 1][tile.c].letter !== null) {
      topR--;
    }
    let bottomR = tile.r;
    while (bottomR < 14 && board[bottomR + 1][tile.c].letter !== null) {
      bottomR++;
    }
    if (topR !== bottomR) {
      const vCells: { r: number; c: number }[] = [];
      for (let r = topR; r <= bottomR; r++) {
        vCells.push({ r, c: tile.c });
      }
      const wordStr = vCells.map(cell => board[cell.r][cell.c].letter).join("");
      wordsFormed.push({ word: wordStr, cells: vCells });
    }
  } else {
    // Main word
    const mainWordCells: { r: number; c: number }[] = [];
    if (alignment === 'row') {
      const r = rows[0];
      let leftC = Math.min(...cols);
      while (leftC > 0 && board[r][leftC - 1].letter !== null) {
        leftC--;
      }
      let rightC = Math.max(...cols);
      while (rightC < 14 && board[r][rightC + 1].letter !== null) {
        rightC++;
      }
      for (let c = leftC; c <= rightC; c++) {
        mainWordCells.push({ r, c });
      }
    } else {
      const c = cols[0];
      let topR = Math.min(...rows);
      while (topR > 0 && board[topR - 1][c].letter !== null) {
        topR--;
      }
      let bottomR = Math.max(...rows);
      while (bottomR < 14 && board[bottomR + 1][c].letter !== null) {
        bottomR++;
      }
      for (let r = topR; r <= bottomR; r++) {
        mainWordCells.push({ r, c });
      }
    }

    if (mainWordCells.length > 1) {
      const wordStr = mainWordCells.map(cell => board[cell.r][cell.c].letter).join("");
      wordsFormed.push({ word: wordStr, cells: mainWordCells });
    }

    // Cross words
    for (const tile of placedTiles) {
      const crossCells: { r: number; c: number }[] = [];
      if (alignment === 'row') {
        let topR = tile.r;
        while (topR > 0 && board[topR - 1][tile.c].letter !== null) {
          topR--;
        }
        let bottomR = tile.r;
        while (bottomR < 14 && board[bottomR + 1][tile.c].letter !== null) {
          bottomR++;
        }
        if (topR !== bottomR) {
          for (let r = topR; r <= bottomR; r++) {
            crossCells.push({ r, c: tile.c });
          }
        }
      } else {
        let leftC = tile.c;
        while (leftC > 0 && board[tile.r][leftC - 1].letter !== null) {
          leftC--;
        }
        let rightC = tile.c;
        while (rightC < 14 && board[tile.r][rightC + 1].letter !== null) {
          rightC++;
        }
        if (leftC !== rightC) {
          for (let c = leftC; c <= rightC; c++) {
            crossCells.push({ r: tile.r, c });
          }
        }
      }

      if (crossCells.length > 1) {
        const wordStr = crossCells.map(cell => board[cell.r][cell.c].letter).join("");
        wordsFormed.push({ word: wordStr, cells: crossCells });
      }
    }
  }

  if (wordsFormed.length === 0) {
    return {
      success: false,
      error: "Tiles must form a word of at least 2 letters."
    };
  }

  // 5. Calculate scores for all words formed
  let turnScore = 0;
  const wordStrings: string[] = [];

  for (const word of wordsFormed) {
    let wordSum = 0;
    let wordMult = 1;

    for (const cell of word.cells) {
      const sq = board[cell.r][cell.c];
      const letterVal = LETTER_VALUES[sq.letter!] || 0;

      // Check if this cell is newly placed (not locked)
      const isNew = placedTiles.some(t => t.r === cell.r && t.c === cell.c);

      if (isNew) {
        if (sq.multiplier === Multiplier.double_letter) {
          wordSum += letterVal * 2;
        } else if (sq.multiplier === Multiplier.triple_letter) {
          wordSum += letterVal * 3;
        } else {
          wordSum += letterVal;
        }

        if (sq.multiplier === Multiplier.double_word) {
          wordMult *= 2;
        } else if (sq.multiplier === Multiplier.triple_word) {
          wordMult *= 3;
        }
      } else {
        wordSum += letterVal;
      }
    }

    turnScore += wordSum * wordMult;
    wordStrings.push(word.word);
  }

  if (placedTiles.length === 7) {
    turnScore += 50; // Bingo bonus!
  }

  return {
    success: true,
    score: turnScore,
    words: wordStrings
  };
}

let wordsSet: Set<string> | null = null;
let loadingPromise: Promise<Set<string>> | null = null;

export async function loadWords(): Promise<Set<string>> {
  if (wordsSet) return wordsSet;
  if (loadingPromise) return loadingPromise;

  loadingPromise = (async () => {
    try {
      const response = await fetch("/words.txt");
      if (!response.ok) {
        throw new Error("Failed to load words.txt");
      }
      const text = await response.text();
      // Split by lines, normalize to lowercase, and filter empty lines
      const words = text.split(/\r?\n/).map(w => w.trim().toLowerCase()).filter(Boolean);
      wordsSet = new Set(words);
      return wordsSet;
    } catch (err) {
      console.error("Failed to load words list locally", err);
      wordsSet = new Set();
      return wordsSet;
    }
  })();

  return loadingPromise;
}

export async function checkWordReal(word: string): Promise<boolean> {
  const cleanWord = word.trim().toLowerCase();
  // Quick local checks for very short single/double letter artifacts
  if (cleanWord.length <= 1) return false;
  
  try {
    const dict = await loadWords();
    return dict.has(cleanWord);
  } catch (e) {
    console.error("Local dictionary check failed", e);
    return true; // fallback to true to not block the user if something goes wrong
  }
}
