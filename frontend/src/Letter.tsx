import { useState } from "react";

type LetterProps = {
  letter: string;
  value: number;
  isSelected: boolean;
  onClick?: () => void;
  isTranslucent?: boolean;
  fallInDelayMs?: number;
};

export default function Letter({ letter, value, isSelected, onClick, isTranslucent, fallInDelayMs }: LetterProps) {
  return (
    <div 
      className={`letter ${isSelected ? 'selected' : ''} ${isTranslucent ? 'translucent-letter' : ''} ${fallInDelayMs !== undefined ? 'last-play-letter' : ''}`}
      onClick={onClick}
      style={fallInDelayMs !== undefined ? { animationDelay: `${fallInDelayMs}ms` } : undefined}
    >
      <div className="letter-content">
        <div className="letter-text">{letter}</div>
        <div className="letter-value">{value}</div>
      </div>
    </div>
  );
}
