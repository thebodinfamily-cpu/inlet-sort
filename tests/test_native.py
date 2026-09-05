"""Tests for the optional native C extension.

These tests are skipped automatically when the extension was not built
(pure-Python-only install). When present, they check that the native sort
matches Python's stable ``sorted()`` oracle, is stable, propagates errors,
and leaves the list untouched on failure.
"""

from __future__ import annotations

import random

import pytest

import inlet_sort.sort as sort_module

_native_sort = sort_module._native_sort

pytestmark = pytest.mark.skipif(
    _native_sort is None, reason="native extension not built"
)


class Keyed:
    """Compares only on ``k`` but carries a distinct ``tag`` to expose order."""

    def __init__(self, k: int, tag: int) -> None:
        self.k = k
        self.tag = tag

    def __lt__(self, other: Keyed) -> bool:
        return self.k < other.k

    def __gt__(self, other: Keyed) -> bool:
        return self.k > other.k


def test_native_backend_is_active() -> None:
    assert _native_sort is not None


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("size", [0, 1, 2, 33, 500, 4000])
def test_matches_sorted(reverse: bool, size: int) -> None:
    rng = random.Random(size + int(reverse))
    data = [rng.randrange(1000) for _ in range(size)]
    result = list(data)
    _native_sort(result, reverse)
    assert result == sorted(data, reverse=reverse)


@pytest.mark.parametrize("reverse", [False, True])
def test_native_is_stable(reverse: bool) -> None:
    rng = random.Random(99 + int(reverse))
    for _ in range(50):
        n = rng.randint(0, 600)
        data = [Keyed(rng.randint(0, 6), i) for i in range(n)]
        result = list(data)
        _native_sort(result, reverse)
        expected = sorted(data, key=lambda item: item.k, reverse=reverse)
        assert [item.tag for item in result] == [item.tag for item in expected]


def test_incomparable_types_raise_and_preserve_list() -> None:
    data = [3, "x", 1]
    with pytest.raises(TypeError):
        _native_sort(data, False)
    assert data == [3, "x", 1]


def test_comparison_error_propagates_and_preserves_list() -> None:
    class Boom:
        def __lt__(self, other: object) -> bool:
            raise ValueError("boom")

        def __gt__(self, other: object) -> bool:
            raise ValueError("boom")

    data = [Boom() for _ in range(40)]
    snapshot = list(data)
    with pytest.raises(ValueError, match="boom"):
        _native_sort(data, False)
    assert data == snapshot


def test_non_list_argument_rejected() -> None:
    with pytest.raises(TypeError):
        _native_sort((3, 1, 2), False)


def test_inlet_sort_uses_native_and_matches_sorted() -> None:
    from inlet_sort import inlet_sort

    rng = random.Random(2026)
    data = [rng.randrange(10_000) for _ in range(5000)]
    assert inlet_sort(data) == sorted(data)
    assert inlet_sort(data, reverse=True) == sorted(data, reverse=True)
