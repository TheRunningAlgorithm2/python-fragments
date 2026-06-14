# Benchmarks

Two benchmarks are included: one measuring the cost of transpilation (a one-time import-time cost), and one measuring the cost of calling a transpiled function at runtime.

All results were measured on a single machine and will vary by hardware. Run the benchmarks yourself to get numbers for your environment.

## Transpilation

Measures how long `transpile()` takes to convert a fragments source file into Python. This cost is paid once per file at import time, not on every request.

**Source:** `benchmarks/transpilation/sample.py`: a realistic file with two components, a `for` loop, interpolations, and an HTML comment.

```bash
python benchmarks/transpilation/benchmark.py
```

```
Transpiler benchmark (5000 iterations × 5 repeats)
  Fragments: 138.1 µs
  Jinja2:    994.6 µs
```

Fragments transpiles a file like this in 138.1 µs — about 7× faster than Jinja2 compiles an equivalent template. At 7,200 transpilations per second, a file can be transpiled 1,200 times per character typed at a fast typing speed — this will never be the limiting factor in LSP or IDE performance.

## Calls

Measures how long a transpiled fragment function takes to execute at runtime compared to an equivalent plain string interpolation. This is the cost paid on every request.

**Source:** `benchmarks/calls/sample.py`: three functions that each render a list of three posts with a heading, byline, and summary: one using fragments, one using Jinja2, and one using `str.format()`.

```bash
python benchmarks/calls/benchmark.py
```

```
Call benchmark (10000 iterations × 5 repeats)
  Fragments:            2.2 µs
  Jinja2:               5.6 µs
  String interpolation: 0.7 µs
```

Fragments adds a small overhead over raw string interpolation and is significantly faster than Jinja2. For a typical web request this cost is negligible: at 2.2 µs per render, a single millisecond of request budget can fit ~454 fragment renders.
