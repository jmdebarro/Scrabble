import { Square, LETTER_VALUES } from "./boardLogic";
import Letter from "./Letter";

interface BoardProps {
  board: Square[][];
  onSquareClick: (r: number, c: number) => void;
}

export default function Board({ board, onSquareClick }: BoardProps) {
  return (
    <div className="board">
      {board.map((row, r) => (
        <div key={r} className="board-row">
          {row.map((square, c) => {
            const hasLetter = square.letter !== null;
            const multiplierClass = getMultiplierClass(square.multiplier);
            const lockClass = square.isLocked ? "locked" : "unlocked";
            const centerClass = (r === 7 && c === 7) ? "center-star" : "";

            return (
              <div 
                className={`square ${multiplierClass} ${centerClass} ${hasLetter ? 'has-letter' : 'empty'} ${lockClass}`}
                key={`${r}-${c}`}
                onClick={!hasLetter ? () => onSquareClick(r, c) : undefined}
              >
                {hasLetter ? (
                  <Letter
                    letter={square.letter!}
                    value={LETTER_VALUES[square.letter!] || 0}
                    isSelected={false}
                    onClick={() => onSquareClick(r, c)}
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
