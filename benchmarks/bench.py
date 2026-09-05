#!/usr/bin/env python3
"""Compare Inlet Sort against Python's built-in sorted().

Reports the native C extension (when built) and the pure-Python
implementation side by side so the speedup from the port is visible.
"""

from __future__ import annotations

import contextlib
import random
import statistics
import time
from collections.abc import Callable, Iterator

import inlet_sort.sort as sort_module
from inlet_sort import inlet_sort


@contextlib.contextmanager
def _force_pure_python() -> Iterator[None]:
    """Temporarily disable the native backend so the pure path is measured."""
    saved = sort_module._native_sort
    sort_module._native_sort = None
    try:
        yield
    finally:
        sort_module._native_sort = saved


def _time_ms(fn: Callable[[], object], repeats: int = 5) -> float:
    samples: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000)
    return statistics.median(samples)


def main() -> None:
    rng = random.Random(2026)
    n = 8_000
    distributions: dict[str, list[int]] = {
        "uniform": [rng.randrange(1_000_000) for _ in range(n)],
        "few unique": [rng.randrange(8) for _ in range(n)],
        "sorted": list(range(n)),
        "reversed": list(range(n, 0, -1)),
        "pipe-organ": list(range(n // 2)) + list(range(n // 2, 0, -1)),
    }

    has_native = sort_module._native_sort is not None
    print(f"n = {n:,}  (median of 5 runs)")
    print(f"native extension: {'yes' if has_native else 'no (pure Python only)'}")
    header = f"{'distribution':<12} {'native':>11} {'pure-py':>11} {'sorted()':>11}"
    print(header)
    print("-" * len(header))
    for name, data in distributions.items():
        native_ms = _time_ms(lambda payload=data: inlet_sort(payload))
        with _force_pure_python():
            pure_ms = _time_ms(lambda payload=data: inlet_sort(payload))
        builtin_ms = _time_ms(lambda payload=data: sorted(payload))
        native_col = f"{native_ms:9.2f}ms" if has_native else f"{'-':>11}"
        print(f"{name:<12} {native_col} {pure_ms:9.2f}ms {builtin_ms:9.2f}ms")


if __name__ == "__main__":
    main()
