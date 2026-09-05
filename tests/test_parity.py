"""Randomized parity tests: native backend vs pure Python vs sorted().

The native C extension must be a drop-in replacement for the pure-Python
samplesort. These tests fuzz a range of distributions, sizes, and element
types, asserting that the native result, the pure-Python result, and
``sorted()`` all agree -- including stability among equal keys.

When the extension is not built, the native/pure comparison is skipped and
only the pure-Python-vs-sorted() check runs.
"""

from __future__ import annotations

import random
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

import inlet_sort.sort as sort_module
from inlet_sort import inlet_sort

_NATIVE_AVAILABLE = sort_module._native_sort is not None


@contextmanager
def _backend(native: bool) -> Iterator[None]:
    """Force the native or pure-Python backend for the duration of the block."""
    saved = sort_module._native_sort
    if not native:
        sort_module._native_sort = None
    try:
        yield
    finally:
        sort_module._native_sort = saved


def _make(kind: str, n: int, rng: random.Random) -> list[object]:
    if kind == "int":
        return [rng.randrange(-1_000_000, 1_000_000) for _ in range(n)]
    if kind == "small_int":
        return [rng.randrange(8) for _ in range(n)]
    if kind == "float":
        return [rng.random() * 2000 - 1000 for _ in range(n)]
    if kind == "string":
        alphabet = "abcXYZ_ "
        return [
            "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 6)))
            for _ in range(n)
        ]
    if kind == "sorted":
        return list(range(n))
    if kind == "reversed":
        return list(range(n, 0, -1))
    if kind == "dup_max":
        head = n // 4 or 1
        return list(range(head)) + [10**9] * (n - head)
    if kind == "pipe_organ":
        return list(range(n // 2)) + list(range(n // 2, 0, -1))
    raise AssertionError(f"unknown kind: {kind}")


_KINDS = [
    "int",
    "small_int",
    "float",
    "string",
    "sorted",
    "reversed",
    "dup_max",
    "pipe_organ",
]


@pytest.mark.parametrize("kind", _KINDS)
@pytest.mark.parametrize("reverse", [False, True])
def test_native_matches_pure_and_sorted(kind: str, reverse: bool) -> None:
    rng = random.Random(hash((kind, reverse)) & 0xFFFF)
    for _ in range(40):
        n = rng.randint(0, 1200)
        data = _make(kind, n, rng)
        expected = sorted(data, reverse=reverse)

        with _backend(native=False):
            pure = inlet_sort(data, reverse=reverse)
        assert pure == expected, (kind, reverse, n)

        if _NATIVE_AVAILABLE:
            with _backend(native=True):
                native = inlet_sort(data, reverse=reverse)
            assert native == expected, (kind, reverse, n)
            assert native == pure, (kind, reverse, n)


class _Keyed:
    """Compares only on ``k`` but carries a distinct ``tag`` to expose order."""

    def __init__(self, k: int, tag: int) -> None:
        self.k = k
        self.tag = tag

    def __lt__(self, other: _Keyed) -> bool:
        return self.k < other.k

    def __gt__(self, other: _Keyed) -> bool:
        return self.k > other.k


@pytest.mark.parametrize("reverse", [False, True])
def test_stability_parity(reverse: bool) -> None:
    rng = random.Random(1234 + int(reverse))
    for _ in range(60):
        n = rng.randint(0, 600)
        data = [_Keyed(rng.randint(0, 6), i) for i in range(n)]
        expected_tags = [
            item.tag for item in sorted(data, key=lambda item: item.k, reverse=reverse)
        ]

        with _backend(native=False):
            pure_tags = [item.tag for item in inlet_sort(data, reverse=reverse)]
        assert pure_tags == expected_tags

        if _NATIVE_AVAILABLE:
            with _backend(native=True):
                native_tags = [item.tag for item in inlet_sort(data, reverse=reverse)]
            assert native_tags == expected_tags
