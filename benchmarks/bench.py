#!/usr/bin/env python3
"""Compare Inlet Sort against Python's built-in sorted()."""

from __future__ import annotations

import random
import statistics
import time
from collections.abc import Callable

from inlet_sort import inlet_sort


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

    print(f"n = {n:,}  (median of 5 runs)")
    print(f"{'distribution':<12} {'inlet-sort':>12} {'sorted()':>12} {'ratio':>8}")
    print("-" * 48)
    for name, data in distributions.items():
        inlet_ms = _time_ms(lambda payload=data: inlet_sort(payload))
        builtin_ms = _time_ms(lambda payload=data: sorted(payload))
        ratio = inlet_ms / builtin_ms if builtin_ms else float("inf")
        print(f"{name:<12} {inlet_ms:10.2f}ms {builtin_ms:10.2f}ms {ratio:8.2f}x")


if __name__ == "__main__":
    main()
