import { Square, LETTER_VALUES } from "./boardLogic";
import Letter from "./Letter";

interface BoardProps {
  board: Square[][];
  onSquareClick: (r: number, c: number) => void;
  highlightedSquares?: { r: number; c: number }[];
  recommendedTiles?: { r: number; c: number; letter: string; isBlank: boolean }[];
  validWordSquares?: { r: number; c: number }[];
}

export default function Board({ board, onSquareClick, highlightedSquares, recommendedTiles, validWordSquares }: BoardProps) {
  return (
    <div className="board">
      {board.map((row, r) => (
        <div key={r} className="board-row">
          {row.map((square, c) => {
            const hasLetter = square.letter !== null;
            const recTile = highlightedSquares && highlightedSquares.length > 0
              ? recommendedTiles?.find(rt => rt.r === r && rt.c === c)
              : null;

            const multiplierClass = getMultiplierClass(square.multiplier);
            const lockClass = square.isLocked ? "locked" : "unlocked";
            const centerClass = (r === 7 && c === 7) ? "center-star" : "";
            const isHighlighted = highlightedSquares?.some(hs => hs.r === r && hs.c === c) || false;
            const highlightClass = isHighlighted ? "highlighted-square" : "";
            const isValidWordSquare = validWordSquares?.some(vs => vs.r === r && vs.c === c) || false;
            const validWordClass = isValidWordSquare ? "valid-word-square" : "";

            return (
              <div 
                className={`square ${multiplierClass} ${centerClass} ${hasLetter ? 'has-letter' : 'empty'} ${lockClass} ${highlightClass} ${validWordClass}`}
                key={`${r}-${c}`}
                onClick={!hasLetter && !recTile ? () => onSquareClick(r, c) : undefined}
              >
                {hasLetter ? (
                  <Letter
                    letter={square.letter!}
                    value={square.isBlank ? 0 : LETTER_VALUES[square.letter!] || 0}
                    isSelected={false}
                    onClick={() => onSquareClick(r, c)}
                  />
                ) : recTile ? (
                  <Letter
                    letter={recTile.letter}
                    value={recTile.isBlank ? 0 : LETTER_VALUES[recTile.letter] || 0}
                    isSelected={false}
                    isTranslucent={true}
                  />
                ) : (
                  <span className="multiplier-label">
                    {getMultiplierLabel(square.multiplier, r, c)}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}

function getMultiplierClass(multiplier: Square['multiplier']): string {
  switch (multiplier) {
    case 'double_letter': return 'double-letter';
    case 'triple_letter': return 'triple-letter';
    case 'double_word': return 'double-word';
    case 'triple_word': return 'triple-word';
    default: return '';
  }
}

function getMultiplierLabel(multiplier: Square['multiplier'], r: number, c: number): string {
  if (r === 7 && c === 7) return "★";
  switch (multiplier) {
    case 'double_letter': return '2L';
    case 'triple_letter': return '3L';
    case 'double_word': return '2W';
    case 'triple_word': return '3W';
    default: return '';
  }
}
