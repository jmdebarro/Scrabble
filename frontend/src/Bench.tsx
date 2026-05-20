import { useState } from 'react';

type BenchProp = {
    initialLetters: string[]
}

export default function Bench({ initialLetters }: BenchProp) {
    const [letters, setLetters] = useState(initialLetters)

    return (
        <>
        <div>
            {letters.map((l, i) => (
                <span key={i}>{l}</span>
            ))}
        </div>
        </>
    )
}

