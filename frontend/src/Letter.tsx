import { useState } from "react";

type LetterProps = {
  letter: string;
  value: number;
  isSelected: boolean;
  onClick?: () => void;
  isTranslucent?: boolean;
};

export default function Letter({ letter, value, isSelected, onClick, isTranslucent }: LetterProps) {
  return (
    <div 
      className={`letter ${isSelected ? 'selected' : ''} ${isTranslucent ? 'translucent-letter' : ''}`}
      onClick={onClick}
    >
      <div className="letter-content">
        <div className="letter-text">{letter}</div>
        <div className="letter-value">{value}</div>
      </div>
    </div>
  );
}