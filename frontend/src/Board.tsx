

enum Multiplier {
  double_letter = "double_letter",
  triple_letter = "triple_letter",
  double_word = "double_word",
  triple_word = "triple_word",
  none = "none"
}

type PropType = {value: Multiplier | null }

const letterValues: Record<string, number> = {
    "A": 1, "E": 1, "I": 1, "O": 1, "U": 1, "L": 1, "N": 1, "S": 1, "T": 1, "R": 1,
    "D": 2, "G": 2,
    "B": 3, "C": 3, "M": 3, "P": 3,
    "F": 4, "H": 4, "V": 4, "W": 4, "Y": 4,
    "K": 5,
    "J": 8, "X": 8,
    "Q": 10, "Z": 10,
    "_": 0
}

const squareValues: Record<Multiplier, string> = {
    [Multiplier.double_letter]: "2L",
    [Multiplier.triple_letter]: "3L",
    [Multiplier.double_word]: "2W",
    [Multiplier.triple_word]: "3W",
    [Multiplier.none]: ""
}

function Square({ value }: PropType) {
  return <div className="square">{value !== null ? squareValues[value] : ""}</div>;
}

const BOARD_LAYOUT: Multiplier[][]

export default function Board() {
  return (
    <>
      <div className="board-row">
        <Square value={Multiplier.triple_word}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
      </div>
      <div className="board-row">
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
      </div>
      <div className="board-row">
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
      </div>
      <div className="board-row">
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
      </div>
      <div className="board-row">
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
      </div>
      <div className="board-row">
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
      </div>
      <div className="board-row">
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
      </div>
      <div className="board-row">
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
      </div>
      <div className="board-row">
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
      </div>
      <div className="board-row">
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
      </div>
      <div className="board-row">
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
      </div>
      <div className="board-row">
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
      </div>
      <div className="board-row">
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
      </div>
      <div className="board-row">
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
      </div>
      <div className="board-row">
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
        <Square value={Multiplier.none}/>
      </div>
    </>
  );
}
