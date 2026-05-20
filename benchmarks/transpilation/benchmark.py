"""Benchmark: time how long the transpiler takes on a representative source file."""

import timeit
from pathlib import Path

from fragments.transpiler import transpile

SOURCE = (Path(__file__).parent / "sample.py").read_text()

ITERATIONS = 1000
REPEATS = 5

if __name__ == "__main__":
    times = timeit.repeat(
        stmt="transpile(SOURCE)",
        globals={"transpile": transpile, "SOURCE": SOURCE},
        number=ITERATIONS,
        repeat=REPEATS,
    )

    average_per_call = sum(times) / (ITERATIONS * REPEATS) * 1_000_000  # microseconds

    print(f"Transpiler benchmark ({ITERATIONS} iterations × {REPEATS} repeats)")
    print(f"  Average per call: {average_per_call:.1f} µs")
