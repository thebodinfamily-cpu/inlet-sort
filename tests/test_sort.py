"""Correctness tests for Inlet Sort vs Python's stable sorted()."""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence

import pytest

from inlet_sort import inlet_sort, inlet_sort_inplace


def _assert_matches_sorted(
    data: Sequence[object],
    *,
    key: Callable[[object], object] | None = None,
    reverse: bool = False,
) -> None:
    expected = sorted(data, key=key, reverse=reverse)
    assert inlet_sort(data, key=key, reverse=reverse) == expected

    clone = list(data)
    inlet_sort_inplace(clone, key=key, reverse=reverse)
    assert clone == expected


@pytest.mark.parametrize(
    "data",
    [
        [],
        [1],
        [2, 1],
        [1, 2],
        [1, 1],
        [3, 1, 2],
        list(range(32)),
        list(range(31, -1, -1)),
        [0] * 50,
        [5, 4, 5, 4, 5],
    ],
)
def test_small_integer_cases(data: list[int]) -> None:
    _assert_matches_sorted(data)
    _assert_matches_sorted(data, reverse=True)


def test_already_sorted_and_reversed() -> None:
    ascending = list(range(200))
    descending = list(range(199, -1, -1))
    _assert_matches_sorted(ascending)
    _assert_matches_sorted(descending)
    _assert_matches_sorted(ascending, reverse=True)
    _assert_matches_sorted(descending, reverse=True)


def test_duplicates_and_stability() -> None:
    pairs = [(value % 5, index) for index, value in enumerate(range(80))]
    # Stable sort keeps original order among equal keys.
    _assert_matches_sorted(pairs, key=lambda item: item[0])
    _assert_matches_sorted(pairs, key=lambda item: item[0], reverse=True)


def test_strings() -> None:
    words = ["pear", "apple", "fig", "apple", "Date", "banana", ""]
    _assert_matches_sorted(words)
    _assert_matches_sorted(words, key=str.lower)
    _assert_matches_sorted(words, reverse=True)


def test_floats_and_negatives() -> None:
    values = [-2.5, 0.0, 3.14, -0.0, 2.5, -10.0, 2.5]
    _assert_matches_sorted(values)
    _assert_matches_sorted(values, reverse=True)


def test_random_distributions() -> None:
    rng = random.Random(2026)
    size = 500
    cases = {
        "uniform": [rng.randrange(10_000) for _ in range(size)],
        "few_unique": [rng.randrange(7) for _ in range(size)],
        "all_equal": [42] * size,
        "sorted": list(range(size)),
        "reversed": list(range(size, 0, -1)),
        "pipe_organ": list(range(size // 2)) + list(range(size // 2, 0, -1)),
        "exponential": [int(2 ** (rng.random() * 12)) for _ in range(size)],
        "negatives": [rng.randint(-500, 500) for _ in range(size)],
    }
    for data in cases.values():
        _assert_matches_sorted(data)
        _assert_matches_sorted(data, reverse=True)


def test_many_copies_of_the_maximum() -> None:
    data = list(range(20)) + [999] * 400
    _assert_matches_sorted(data)
    _assert_matches_sorted(data, reverse=True)


def test_large_input() -> None:
    rng = random.Random(7)
    data = [rng.randrange(1_000_000) for _ in range(8_000)]
    _assert_matches_sorted(data)


def test_key_only_compares_keys() -> None:
    class Unordered:
        def __init__(self, label: str) -> None:
            self.label = label

        def __lt__(self, other: object) -> bool:
            raise TypeError("values are not ordered")

    items = [Unordered("b"), Unordered("a"), Unordered("b"), Unordered("c")]
    ordered = inlet_sort(items, key=lambda item: item.label)
    assert [item.label for item in ordered] == ["a", "b", "b", "c"]


def test_inplace_does_not_replace_list_identity() -> None:
    data = [3, 1, 2]
    original = data
    inlet_sort_inplace(data)
    assert data is original
    assert data == [1, 2, 3]


def test_iterable_input_is_not_consumed_requirement() -> None:
    result = inlet_sort(range(5, 0, -1))
    assert result == [1, 2, 3, 4, 5]


def test_stability_with_identical_objects() -> None:
    items = [("x", 1), ("x", 2), ("y", 3), ("x", 4)]
    ordered = inlet_sort(items, key=lambda item: item[0])
    assert ordered == [("x", 1), ("x", 2), ("x", 4), ("y", 3)]
    reversed_order = inlet_sort(items, key=lambda item: item[0], reverse=True)
    assert reversed_order == [("y", 3), ("x", 1), ("x", 2), ("x", 4)]
