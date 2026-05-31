"""Benchmark: time how long a transpiled function takes to execute at runtime."""

import timeit

from fragments import loader  # noqa: F401  # isort: skip
import sample

ITERATIONS = 10_000
REPEATS = 5


if __name__ == "__main__":
    fragments_times = timeit.repeat(
        stmt="sample.Articles()",
        globals={"sample": sample},
        number=ITERATIONS,
        repeat=REPEATS,
    )
    jinja_times = timeit.repeat(
        stmt="sample.ArticlesJinja()",
        globals={"sample": sample},
        number=ITERATIONS,
        repeat=REPEATS,
    )
    string_times = timeit.repeat(
        stmt="sample.ArticlesStringOnly()",
        globals={"sample": sample},
        number=ITERATIONS,
        repeat=REPEATS,
    )

    fragments_average = sum(fragments_times) / (ITERATIONS * REPEATS) * 1_000_000  # microseconds
    jinja_average = sum(jinja_times) / (ITERATIONS * REPEATS) * 1_000_000  # microseconds
    string_average = sum(string_times) / (ITERATIONS * REPEATS) * 1_000_000  # microseconds

    print(f"Call benchmark ({ITERATIONS} iterations × {REPEATS} repeats)")
    print(f"  Fragments:            {fragments_average:.1f} µs")
    print(f"  Jinja2:               {jinja_average:.1f} µs")
    print(f"  String interpolation: {string_average:.1f} µs")
