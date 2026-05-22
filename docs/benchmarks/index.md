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
Transpiler benchmark (1000 iterations × 5 repeats)
  Average per call: 121.0 µs
```

A simple file like this can be transpiled fully 8,000 times per second. At a typing speed of 400 characters per minute (fast, 6 characters per second, 1 character every 0.15 seconds) the file you're working on can be transpiled 1,200 times per character typed - this will never be the limiting factor in LSP or IDE performance.

## Calls

Measures how long a transpiled fragment function takes to execute at runtime compared to an equivalent plain string interpolation. This is the cost paid on every request.

**Source:** `benchmarks/calls/sample.py`: two functions that each render a list of three posts with a heading, byline, and summary: one using fragments, one using `str.format()`.

```bash
python benchmarks/calls/benchmark.py
```

```
Call benchmark (10000 iterations × 5 repeats)
  Fragments:            10.6 µs
  String interpolation:  0.7 µs
```

Fragments adds overhead over raw string interpolation because it uses the HTML library (`el`, `sequence`) to build and join elements safely. For a typical web request this cost is negligible: at 10 µs per render, a single millisecond of request budget can fit ~100 fragment renders.
