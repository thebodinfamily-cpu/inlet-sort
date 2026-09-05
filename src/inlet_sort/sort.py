"""Core Inlet Sort implementation.

Inlet Sort is a sequential samplesort. Values flow through a classifying
inlet that routes each item into one of several ordered chambers
(inlets) based on sampled quantiles. Small inlets are insertion-sorted;
larger ones are sorted recursively. Equal keys stay in input order.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, MutableSequence
from typing import TypeVar

T = TypeVar("T")
K = TypeVar("K")

_BASE_CASE = 32
_MAX_INLETS = 64
_OVERSAMPLE = 4
_MIN_INLETS = 2


def inlet_sort(
    iterable: Iterable[T],
    /,
    *,
    key: Callable[[T], K] | None = None,
    reverse: bool = False,
) -> list[T]:
    """Return a new list containing all items from *iterable* in sorted order.

    The signature matches :func:`sorted`: *key* extracts a comparison key
    and *reverse* sorts descending. Equal keys keep their original order.
    """
    values = list(iterable)
    inlet_sort_inplace(values, key=key, reverse=reverse)
    return values


def inlet_sort_inplace(
    values: MutableSequence[T],
    /,
    *,
    key: Callable[[T], K] | None = None,
    reverse: bool = False,
) -> None:
    """Sort *values* in place using Inlet Sort.

    Extra memory is O(n) for the inlet buffers. Falls back to a stable
    insertion sort for tiny ranges and to :func:`sorted` if recursion
    would go too deep (introsort-style safety).
    """
    n = len(values)
    if n < 2:
        return

    if key is None:
        less = _gt if reverse else _lt
        _sort_range(values, 0, n, less, depth_limit=_max_depth(n))
        return

    decorated: list[tuple[K, T]] = [(key(item), item) for item in values]
    key_less = _gt if reverse else _lt

    def decorated_less(left: tuple[K, T], right: tuple[K, T]) -> bool:
        return key_less(left[0], right[0])

    _sort_range(decorated, 0, n, decorated_less, depth_limit=_max_depth(n))
    for index, (_, item) in enumerate(decorated):
        values[index] = item


def _lt(left: object, right: object) -> bool:
    return bool(left < right)  # type: ignore[operator]


def _gt(left: object, right: object) -> bool:
    return bool(left > right)  # type: ignore[operator]


def _is_nondecreasing(
    values: MutableSequence[T],
    lo: int,
    hi: int,
    less: Callable[[T, T], bool],
) -> bool:
    return all(not less(values[i], values[i - 1]) for i in range(lo + 1, hi))


def _max_depth(n: int) -> int:
    depth = 0
    while n > 1:
        n //= 2
        depth += 1
    return 2 * depth + 8


def _sort_range(
    values: MutableSequence[T],
    lo: int,
    hi: int,
    less: Callable[[T, T], bool],
    depth_limit: int,
) -> None:
    n = hi - lo
    if n < 2:
        return
    if n <= _BASE_CASE:
        _insertion_sort(values, lo, hi, less)
        return
    if _is_nondecreasing(values, lo, hi, less):
        return
    if depth_limit <= 0:
        _stable_fallback(values, lo, hi, less)
        return

    splitters = _choose_splitters(values, lo, hi, less)
    if not splitters:
        _partition_equal_sample(values, lo, hi, less, depth_limit)
        return

    inlets = _scatter(values, lo, hi, splitters, less)
    if max(len(inlet) for inlet in inlets) == n:
        # Splitters were in-range but did not partition (e.g. the only
        # splitter is the maximum). Isolate equals around a pivot instead.
        _partition_equal_sample(values, lo, hi, less, depth_limit)
        return

    write = lo
    for inlet in inlets:
        size = len(inlet)
        if size == 0:
            continue
        values[write : write + size] = inlet
        end = write + size
        if size > 1 and _range_needs_sort(values, write, end, less):
            _sort_range(values, write, end, less, depth_limit - 1)
        write = end


def _choose_splitters(
    values: MutableSequence[T],
    lo: int,
    hi: int,
    less: Callable[[T, T], bool],
) -> list[T]:
    n = hi - lo
    inlet_count = min(_MAX_INLETS, max(_MIN_INLETS, n // _BASE_CASE))
    sample_size = min(n, max(inlet_count * _OVERSAMPLE - 1, inlet_count))
    if sample_size < 2:
        return []

    stride = n / sample_size
    sample = [values[lo + min(n - 1, int(i * stride))] for i in range(sample_size)]
    if len(sample) <= 128:
        _insertion_sort(sample, 0, len(sample), less)
    else:
        _stable_fallback(sample, 0, len(sample), less)

    splitter_count = inlet_count - 1
    splitters: list[T] = []
    for rank in range(1, splitter_count + 1):
        index = min(len(sample) - 1, (rank * len(sample)) // (splitter_count + 1))
        candidate = sample[index]
        if not splitters or less(splitters[-1], candidate):
            splitters.append(candidate)
    return splitters


def _scatter(
    values: MutableSequence[T],
    lo: int,
    hi: int,
    splitters: list[T],
    less: Callable[[T, T], bool],
) -> list[list[T]]:
    inlets: list[list[T]] = [[] for _ in range(len(splitters) + 1)]
    for i in range(lo, hi):
        item = values[i]
        inlets[_locate(item, splitters, less)].append(item)
    return inlets


def _locate(item: T, splitters: list[T], less: Callable[[T, T], bool]) -> int:
    lo = 0
    hi = len(splitters)
    while lo < hi:
        mid = (lo + hi) // 2
        if less(splitters[mid], item):
            lo = mid + 1
        else:
            hi = mid
    return lo


def _partition_equal_sample(
    values: MutableSequence[T],
    lo: int,
    hi: int,
    less: Callable[[T, T], bool],
    depth_limit: int,
) -> None:
    """Three-way split around a pivot when the sample could not yield splitters."""
    pivot = values[lo + (hi - lo) // 2]
    lesser: list[T] = []
    equal: list[T] = []
    greater: list[T] = []
    for i in range(lo, hi):
        item = values[i]
        if less(item, pivot):
            lesser.append(item)
        elif less(pivot, item):
            greater.append(item)
        else:
            equal.append(item)

    write = lo
    values[write : write + len(lesser)] = lesser
    left_end = write + len(lesser)
    write = left_end
    values[write : write + len(equal)] = equal
    write += len(equal)
    values[write : write + len(greater)] = greater
    right_start = write

    if len(lesser) > 1:
        _sort_range(values, lo, left_end, less, depth_limit - 1)
    if len(greater) > 1:
        _sort_range(values, right_start, hi, less, depth_limit - 1)


def _range_needs_sort(
    values: MutableSequence[T],
    lo: int,
    hi: int,
    less: Callable[[T, T], bool],
) -> bool:
    first = values[lo]
    for i in range(lo + 1, hi):
        if less(first, values[i]) or less(values[i], first):
            return True
    return False


def _insertion_sort(
    values: MutableSequence[T],
    lo: int,
    hi: int,
    less: Callable[[T, T], bool],
) -> None:
    for i in range(lo + 1, hi):
        current = values[i]
        j = i
        while j > lo and less(current, values[j - 1]):
            values[j] = values[j - 1]
            j -= 1
        values[j] = current


def _stable_fallback(
    values: MutableSequence[T],
    lo: int,
    hi: int,
    less: Callable[[T, T], bool],
) -> None:
    # sorted() is stable. Use a key that encodes the less-than relation
    # without requiring a total order beyond what *less* already defines.
    slice_copy = list(values[lo:hi])

    class _Order:
        __slots__ = ("value",)

        def __init__(self, value: T) -> None:
            self.value = value

        def __lt__(self, other: _Order) -> bool:
            return less(self.value, other.value)

    ordered = sorted(slice_copy, key=_Order)
    values[lo:hi] = ordered
