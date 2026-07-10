import { useState } from "react";

type LetterProps = {
  letter: string;
  value: number;
  isSelected: boolean;
  onClick: () => void;
};

export default function Letter({ letter, value, isSelected, onClick }: LetterProps) {
  return (
    <div 
      className={`letter ${isSelected ? 'selected' : ''}`}
      onClick={onClick}
    >
      <div className="letter-content">
        <div className="letter-text">{letter}</div>
        <div className="letter-value">{value}</div>
      </div>
    </div>
  );
}