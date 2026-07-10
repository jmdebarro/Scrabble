import Letter from "./Letter";
import { LETTER_VALUES } from "./boardLogic";

interface BenchProps {
  bench: (string | null)[];
  selectedBenchIndices: number[];
  onSelectTile: (index: number) => void;
}

export default function Bench({ bench, selectedBenchIndices, onSelectTile }: BenchProps) {
  return (
    <div className="bench">
      {bench.map((letter, index) => {
        if (letter === null) {
          return <div key={index} className="bench-empty-slot" />;
        }
        return (
          <Letter
            key={index}
            letter={letter}
            value={LETTER_VALUES[letter] || 0}
            isSelected={selectedBenchIndices.includes(index)}
            onClick={() => onSelectTile(index)}
          />
        );
      })}
    </div>
  );
}
