"""Benchmark: time how long the transpiler takes on a representative source file."""

import timeit
from pathlib import Path

import jinja2

from fragments.transpiler import transpile

SOURCE = (Path(__file__).parent / "sample.py").read_text()

JINJA_ENVIRONMENT = jinja2.Environment()
JINJA_TEMPLATE = """\
{% macro PostCard(post) %}\
<div>\
<!-- Hello -->\
<h2>{{ post.title }}</h2>\
<p>{{ post.date.strftime("%d-%m-%y") }}</p>\
</div>\
{% endmacro %}\
{% macro page(title, header) %}\
{% for post in posts %}{{ PostCard(post) }}{% endfor %}\
{% endmacro %}\
"""

ITERATIONS = 5000
REPEATS = 5

if __name__ == "__main__":
    transpile_times = timeit.repeat(
        stmt="transpile(SOURCE)",
        globals={"transpile": transpile, "SOURCE": SOURCE},
        number=ITERATIONS,
        repeat=REPEATS,
    )
    jinja_times = timeit.repeat(
        stmt="JINJA_ENVIRONMENT.from_string(JINJA_TEMPLATE)",
        globals={"JINJA_ENVIRONMENT": JINJA_ENVIRONMENT, "JINJA_TEMPLATE": JINJA_TEMPLATE},
        number=ITERATIONS,
        repeat=REPEATS,
    )

    transpile_average = sum(transpile_times) / (ITERATIONS * REPEATS) * 1_000_000  # microseconds
    jinja_average = sum(jinja_times) / (ITERATIONS * REPEATS) * 1_000_000  # microseconds

    print(f"Transpiler benchmark ({ITERATIONS} iterations × {REPEATS} repeats)")
    print(f"  Fragments: {transpile_average:.1f} µs")
    print(f"  Jinja2:    {jinja_average:.1f} µs")
