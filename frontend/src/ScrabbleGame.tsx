import { useState, useEffect } from "react";
import {
  createBoard,
  createTileBag,
  validateAndScoreMove,
  Square,
  PlacedTile,
  checkWordReal
} from "./boardLogic";
import Board from "./Board";
import Bench from "./Bench";

interface PlacedTileInfo {
  r: number;
  c: number;
  letter: string;
  originalIndex: number;
}

interface PlayedWordLog {
  word: string;
  score: number;
}

interface FeedbackMessage {
  text: string;
  type: "success" | "error" | "info";
}

export default function ScrabbleGame() {
  const [gameInitialized, setGameInitialized] = useState(false);
  const [board, setBoard] = useState<Square[][]>([]);
  const [tileBag, setTileBag] = useState<string[]>([]);
  const [bench, setBench] = useState<(string | null)[]>([]);
  const [placedTiles, setPlacedTiles] = useState<PlacedTileInfo[]>([]);
  const [selectedBenchIndices, setSelectedBenchIndices] = useState<number[]>([]);
  
  const [totalScore, setTotalScore] = useState<number>(0);
  const [playedWords, setPlayedWords] = useState<PlayedWordLog[]>([]);
  const [feedback, setFeedback] = useState<FeedbackMessage | null>(null);

  // Initialize game on mount
  useEffect(() => {
    const initialBag = createTileBag();
    const initialBoard = createBoard();
    
    // Draw initial 7 tiles
    const initialBench: (string | null)[] = [];
    const remainingBag = [...initialBag];
    for (let i = 0; i < 7; i++) {
      if (remainingBag.length > 0) {
        initialBench.push(remainingBag.pop()!);
      }
    }

    setBoard(initialBoard);
    setTileBag(remainingBag);
    setBench(initialBench);
    setGameInitialized(true);
    setFeedback({ text: "Welcome to Scrabble! Select a tile and place it on the board.", type: "info" });
  }, []);

  // Handle keyboard shortcuts for selecting tiles from the bench
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (document.activeElement?.tagName === "INPUT" || document.activeElement?.tagName === "TEXTAREA") {
        return;
      }
      const key = e.key;
      
      // 1-7 number keys select by index
      if (key >= "1" && key <= "7") {
        const index = parseInt(key, 10) - 1;
        if (index < bench.length) {
          handleSelectTile(index);
        }
        return;
      }

      // Letter keys or space bar select by character
      if ((key >= "a" && key <= "z") || (key >= "A" && key <= "Z") || key === " ") {
        const targetLetter = key === " " ? " " : key.toUpperCase();
        
        const isMatch = (benchLetter: string | null) => {
          if (!benchLetter) return false;
          if (targetLetter === " ") {
            return benchLetter === " " || benchLetter === "_" || benchLetter === "?";
          }
          return benchLetter.toUpperCase() === targetLetter;
        };

        const matchingIndices = bench
          .map((letter, index) => ({ letter, index }))
          .filter(item => isMatch(item.letter))
          .map(item => item.index);
          
        if (matchingIndices.length > 0) {
          const unselectedMatch = matchingIndices.find(index => !selectedBenchIndices.includes(index));
          if (unselectedMatch !== undefined) {
            handleSelectTile(unselectedMatch);
          } else {
            // If all matching letters are already selected, pressing again deselects the last selected matching one
            const lastSelectedMatch = [...matchingIndices].reverse().find(index => selectedBenchIndices.includes(index));
            if (lastSelectedMatch !== undefined) {
              handleSelectTile(lastSelectedMatch);
            }
          }
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [bench, selectedBenchIndices]);

  if (!gameInitialized) {
    return <div className="loading">Initializing Scrabble Board...</div>;
  }

  const handleSelectTile = (index: number) => {
    if (bench[index] === null) return;
    if (selectedBenchIndices.includes(index)) {
      setSelectedBenchIndices(prev => prev.filter(i => i !== index));
    } else {
      setSelectedBenchIndices(prev => [...prev, index]);
    }
  };

  const handleSquareClick = (r: number, c: number) => {
    const square = board[r][c];

    // Case 1: Clicking an occupied cell
    if (square.letter !== null) {
      if (square.isLocked) {
        setFeedback({ text: "That tile was played in a previous turn and is locked.", type: "error" });
        return;
      }

      // Recall the tile back to the bench
      const tileInfo = placedTiles.find(t => t.r === r && t.c === c);
      if (tileInfo) {
        const newBoard = board.map((row, ri) =>
          row.map((sq, ci) => (ri === r && ci === c ? { ...sq, letter: null } : sq))
        );
        const newBench = [...bench];
        newBench[tileInfo.originalIndex] = tileInfo.letter;

        setBoard(newBoard);
        setBench(newBench);
        setPlacedTiles(prev => prev.filter(t => !(t.r === r && t.c === c)));
        setSelectedBenchIndices(prev => prev.filter(i => i !== tileInfo.originalIndex));
        setFeedback(null);
      }
      return;
    }

    // Case 2: Clicking an empty cell
    if (selectedBenchIndices.length > 0) {
      const indexToPlace = selectedBenchIndices[0];
      const letterToPlace = bench[indexToPlace];
      if (!letterToPlace) return;

      const newBoard = board.map((row, ri) =>
        row.map((sq, ci) => (ri === r && ci === c ? { ...sq, letter: letterToPlace } : sq))
      );
      const newBench = [...bench];
      newBench[indexToPlace] = null;

      const newTile: PlacedTileInfo = {
        r,
        c,
        letter: letterToPlace,
        originalIndex: indexToPlace
      };

      setBoard(newBoard);
      setBench(newBench);
      setPlacedTiles(prev => [...prev, newTile]);
      setSelectedBenchIndices(prev => prev.filter(i => i !== indexToPlace));
      setFeedback(null);
    }
  };

  const handleRecallAll = () => {
    if (placedTiles.length === 0) return;

    const newBoard = board.map(row => row.map(sq => ({ ...sq })));
    const newBench = [...bench];

    placedTiles.forEach(t => {
      newBoard[t.r][t.c].letter = null;
      newBench[t.originalIndex] = t.letter;
    });

    setBoard(newBoard);
    setBench(newBench);
    setPlacedTiles([]);
    setSelectedBenchIndices([]);
    setFeedback({ text: "Recalled all pending tiles to your rack.", type: "info" });
  };

  const handleShuffle = () => {
    const activeLetters = bench.filter((l): l is string => l !== null);
    
    // Shuffle active letters
    for (let i = activeLetters.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [activeLetters[i], activeLetters[j]] = [activeLetters[j], activeLetters[i]];
    }

    const newBench = [...activeLetters];
    while (newBench.length < 7) {
      newBench.push(null);
    }

    setBench(newBench);
    setSelectedBenchIndices([]);
  };

  const handleExchangeTile = () => {
    if (selectedBenchIndices.length === 0) {
      setFeedback({ text: "Please select one or more tiles on your bench to exchange.", type: "info" });
      return;
    }

    if (tileBag.length < selectedBenchIndices.length) {
      setFeedback({ text: `Not enough tiles in the bag. Only ${tileBag.length} left.`, type: "error" });
      return;
    }

    // Extract selected tiles
    const lettersToSwap = selectedBenchIndices.map(idx => bench[idx]).filter((l): l is string => l !== null);
    const newBag = [...tileBag, ...lettersToSwap];
    
    // Shuffle newBag
    for (let i = newBag.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [newBag[i], newBag[j]] = [newBag[j], newBag[i]];
    }

    const newBench = [...bench];
    selectedBenchIndices.forEach(idx => {
      newBench[idx] = newBag.pop()!;
    });

    setTileBag(newBag);
    setBench(newBench);
    setSelectedBenchIndices([]);
    setFeedback({ text: `Exchanged ${lettersToSwap.length} tile(s) for new ones. Turn passed.`, type: "success" });
  };

  const handleSubmitWord = async () => {
    if (placedTiles.length === 0) {
      setFeedback({ text: "Place some tiles on the board first!", type: "error" });
      return;
    }

    const tilesToValidate: PlacedTile[] = placedTiles.map(t => ({
      r: t.r,
      c: t.c,
      letter: t.letter
    }));

    const result = validateAndScoreMove(board, tilesToValidate);

    if (!result.success) {
      setFeedback({ text: result.error!, type: "error" });
      return;
    }

    // Check with standard dictionary API if the word is real
    setFeedback({ text: "Validating words against dictionary...", type: "info" });
    
    try {
      const words = result.words!;
      const invalidWords: string[] = [];

      for (const word of words) {
        const isReal = await checkWordReal(word);
        if (!isReal) {
          invalidWords.push(word);
        }
      }

      if (invalidWords.length > 0) {
        setFeedback({
          text: `Invalid play! The following word(s) are not real: ${invalidWords.join(", ")}`,
          type: "error"
        });
        return;
      }
    } catch (err) {
      console.error("Dictionary check failed", err);
    }

    // 1. Lock placed tiles
    const newBoard = board.map(row => row.map(sq => ({ ...sq })));
    placedTiles.forEach(t => {
      newBoard[t.r][t.c].isLocked = true;
    });

    // 2. Replenish bench
    const newBag = [...tileBag];
    const newBench = bench.map(letter => {
      if (letter === null && newBag.length > 0) {
        return newBag.pop()!;
      }
      return letter;
    });

    // 3. Update States
    setTotalScore(prev => prev + result.score!);
    setPlayedWords(prev => [
      { word: result.words!.join(", "), score: result.score! },
      ...prev
    ]);
    setBoard(newBoard);
    setTileBag(newBag);
    setBench(newBench);
    setPlacedTiles([]);
    setSelectedBenchIndices([]);
    setFeedback({
      text: `Play confirmed! Word(s): ${result.words!.join(", ")} (+${result.score} pts)`,
      type: "success"
    });
  };

  return (
    <div className="game-container">
      <div className="game-layout">
        
        {/* Board column */}
        <div className="board-column">
          <div className="header-bar">
            <h1>Oh My Pi Scrabble</h1>
          </div>
          
          <Board board={board} onSquareClick={handleSquareClick} />
          
          <div className="rack-area">
            <div className="rack-label">Your Rack</div>
            <Bench
              bench={bench}
              selectedBenchIndices={selectedBenchIndices}
              onSelectTile={handleSelectTile}
            />
          </div>

          <div className="control-panel">
            <button className="btn btn-submit" onClick={handleSubmitWord}>
              Play Word
            </button>
            <button className="btn btn-recall" onClick={handleRecallAll} disabled={placedTiles.length === 0}>
              Recall All
            </button>
            <button className="btn btn-shuffle" onClick={handleShuffle}>
              Shuffle Rack
            </button>
            <button className="btn btn-swap" onClick={handleExchangeTile} disabled={selectedBenchIndices.length === 0}>
              Swap Selected
            </button>
          </div>
        </div>

        {/* Sidebar panel */}
        <div className="sidebar-column">
          <div className="panel score-panel">
            <h3>Player Score</h3>
            <div className="total-score">{totalScore}</div>
            <div className="bag-status">
              Tiles in Bag: <strong>{tileBag.length}</strong>
            </div>
          </div>

          {feedback && (
            <div className={`feedback-alert feedback-${feedback.type}`}>
              {feedback.text}
            </div>
          )}

          <div className="panel word-log-panel">
            <h3>Word History</h3>
            {playedWords.length === 0 ? (
              <p className="no-history">No words played yet.</p>
            ) : (
              <div className="log-list">
                {playedWords.map((log, index) => (
                  <div key={index} className="log-item">
                    <span className="log-word">{log.word}</span>
                    <span className="log-points">+{log.score} pts</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="panel instructions-panel">
            <h3>How to Play</h3>
            <ol>
              <li>Click or press <strong>1-7</strong> to select/deselect letters on your rack.</li>
              <li>Click an empty board square to place your selected letters in order.</li>
              <li>To recall a placed letter, click it on the board.</li>
              <li>Arrange tiles in a continuous straight line.</li>
              <li>The first play of the game must cross the center star (★).</li>
              <li>Subsequent plays must connect to existing tiles.</li>
              <li>Select multiple tiles and click <strong>Swap Selected</strong> to exchange them!</li>
            </ol>
          </div>
        </div>

      </div>
    </div>
  );
}
