# inlet-sort

[![CI](https://github.com/thebodinfamily-cpu/inlet-sort/actions/workflows/ci.yml/badge.svg)](https://github.com/thebodinfamily-cpu/inlet-sort/actions/workflows/ci.yml)

Inlet Sort is a **sequential samplesort**: items flow through a classifying inlet
that routes each value into one of several ordered chambers, then each chamber
is sorted and drained left to right.

Python library, CLI, tests, and CI. Stable, with a `sorted()`-compatible API.

## How it works

```
            sample quantiles
                  │
                  ▼
   ┌──────── inlet (classifier) ────────┐
   │  ≤ s0   │  ≤ s1   │  …  │  > sk-2  │
   └────┬────────┬───────────┬─────┬────┘
        ▼        ▼           ▼     ▼
     inlet 0  inlet 1  …  inlet k-1
        │        │           │
        └────────┴─────┬─────┘
                       ▼
              concatenate in order
```

1. **Base case.** Ranges of 32 items or fewer are insertion-sorted (stable).
   Larger ranges that are already in order return immediately.
2. **Sample.** Evenly spaced items are sorted and used as splitters (quantiles).
3. **Scatter.** Each item is binary-searched into an inlet. Equal keys keep
   input order because inlets are appended left to right.
4. **Drain.** Small inlets are insertion-sorted; large ones recurse. If a sample
   cannot produce splitters (many duplicates), a three-way pivot split isolates
   equals in linear time.
5. **Safety.** Recursion is depth-limited (introsort-style) and falls back to
   Python's stable `sorted()`.

Expected time is **O(n log n)** comparisons. Extra memory is **O(n)** for the
inlet buffers. The algorithm is **stable**.

Python's built-in `sorted()` is a highly tuned Timsort written in C, so it will
usually win on wall-clock time. Inlet Sort is here as a clear, tested samplesort
you can read, teach, and port to a lower-level implementation. An optional C
port of the inlet classifier ships in `src/inlet_sort/_inletsort.c` and closes
much of the gap with the pure-Python version while staying stable.

## Install

```bash
python -m pip install -e ".[dev]"
```

Requires Python 3.10+.

If a C compiler and the Python development headers are available, an optional
native extension (`inlet_sort._inletsort`) is built automatically and used
transparently. It is a faithful, stable port of the same inlet classifier and
runs several times faster than the pure-Python code. The extension is marked
optional: when it cannot be built, installation still succeeds and the
pure-Python implementation is used instead, with identical results.

## Library

```python
from inlet_sort import inlet_sort, inlet_sort_inplace

inlet_sort([3, 1, 2])                      # [1, 2, 3]
inlet_sort(["b", "a"], reverse=True)       # ["b", "a"]
inlet_sort(["Ken", "ada"], key=str.lower)  # ["ada", "Ken"]

data = [3, 1, 2]
inlet_sort_inplace(data)                   # data == [1, 2, 3]
```

`inlet_sort` matches `sorted()`: it accepts any iterable and the `key` /
`reverse` keyword-only arguments. `inlet_sort_inplace` matches `list.sort()`.

## CLI

```bash
inlet-sort numbers.txt --numeric
printf 'pear\napple\npear\n' | inlet-sort -u
python -m inlet_sort -n -r data.txt
```

| Flag | Meaning |
|------|---------|
| `-n` / `--numeric` | Parse each line as an int or float |
| `-r` / `--reverse` | Descending order |
| `-u` / `--unique` | Drop adjacent duplicates after sorting |

## Develop

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
ruff format --check .
mypy
python benchmarks/bench.py
```

## Status

Alpha. The sort is covered against `sorted()` on empty/tiny inputs, duplicates,
stability, strings, floats, skewed distributions, and a few thousand random
integers. A C or Rust port of the same inlet classifier is the natural next step
if you want Timsort-competitive CPU performance.
