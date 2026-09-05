"""Edge-case tests for the native numeric radix fast paths.

The native extension sorts all-int and all-float lists with a stable radix
sort. These tests cover the tricky cases the fuzz/parity suites don't
specifically target: signed zeros, infinities, int64 boundaries, and the
fallbacks (overflowing ints, bools, and mixed int/float lists) that must defer
to the generic comparison sort. All are checked against ``sorted()``.
"""

from __future__ import annotations

import math
import random

import pytest

import inlet_sort.sort as sort_module

_native_sort = sort_module._native_sort

pytestmark = pytest.mark.skipif(
    _native_sort is None, reason="native extension not built"
)


def _check(data: list[object], reverse: bool) -> None:
    result = list(data)
    _native_sort(result, reverse)
    assert result == sorted(data, reverse=reverse)


@pytest.mark.parametrize("reverse", [False, True])
def test_signed_zeros_order_like_sorted(reverse: bool) -> None:
    # -0.0 == 0.0, so a stable sort must preserve their input order.
    _check([0.0, -0.0, 0.0, -0.0], reverse)
    _check([-0.0, 0.0], reverse)
    _check([1.0, -0.0, 0.0, -1.0, 2.5, 2.5], reverse)


@pytest.mark.parametrize("reverse", [False, True])
def test_infinities(reverse: bool) -> None:
    _check([math.inf, -math.inf, 0.0, 1e308, -1e308, math.inf], reverse)


@pytest.mark.parametrize("reverse", [False, True])
def test_int64_boundaries(reverse: bool) -> None:
    _check([-(2**63), 2**63 - 1, 0, -1, 1, 2**62, -(2**62)], reverse)


@pytest.mark.parametrize("reverse", [False, True])
def test_overflowing_ints_fall_back(reverse: bool) -> None:
    # Values outside int64 must defer to the generic sort and stay correct.
    _check([2**70, -(2**80), 5, -3, 2**63, 2**63 - 1, -(2**63)], reverse)


@pytest.mark.parametrize("reverse", [False, True])
def test_bool_list_falls_back(reverse: bool) -> None:
    # bool is a subclass of int (not exact), so this uses the generic path.
    _check([True, False, True, False, True], reverse)


@pytest.mark.parametrize("reverse", [False, True])
def test_mixed_int_float_falls_back(reverse: bool) -> None:
    _check([3, 1.5, 2, 0.5, 3, 1], reverse)


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("kind", ["int", "float"])
def test_fastpath_fuzz_matches_sorted(kind: str, reverse: bool) -> None:
    rng = random.Random(hash((kind, reverse)) & 0xFFFF)
    for _ in range(50):
        n = rng.randint(0, 2000)
        if kind == "int":
            data: list[object] = [rng.randrange(-(10**9), 10**9) for _ in range(n)]
        else:
            data = [rng.uniform(-1e6, 1e6) for _ in range(n)]
        _check(data, reverse)
