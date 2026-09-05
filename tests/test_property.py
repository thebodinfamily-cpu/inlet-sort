"""Property-based tests for Inlet Sort, checked against Python's stable sorted()."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from inlet_sort import inlet_sort, inlet_sort_inplace

_integers = st.integers(min_value=-1000, max_value=1000)
_floats = st.floats(allow_nan=False, allow_infinity=False, width=32)
_texts = st.text(max_size=8)
# Homogeneous lists only: mixing incomparable types is invalid for any
# comparison sort (sorted() itself raises TypeError on such input).
_homogeneous_lists = st.one_of(
    st.lists(_integers, max_size=200),
    st.lists(_floats, max_size=200),
    st.lists(_texts, max_size=200),
)


@given(data=st.lists(_integers, max_size=300))
def test_matches_sorted_integers(data: list[int]) -> None:
    assert inlet_sort(data) == sorted(data)
    assert inlet_sort(data, reverse=True) == sorted(data, reverse=True)


@given(data=st.lists(_floats, max_size=300))
def test_matches_sorted_floats(data: list[float]) -> None:
    assert inlet_sort(data) == sorted(data)
    assert inlet_sort(data, reverse=True) == sorted(data, reverse=True)


@given(data=st.lists(_texts, max_size=200))
def test_matches_sorted_strings(data: list[str]) -> None:
    assert inlet_sort(data) == sorted(data)
    assert inlet_sort(data, key=str.lower) == sorted(data, key=str.lower)


@given(data=_homogeneous_lists)
def test_output_is_a_permutation_of_input(data: list[object]) -> None:
    ordered = inlet_sort(data)
    assert len(ordered) == len(data)
    # Equal multisets: the result reorders the input without adding or dropping.
    assert sorted(map(repr, ordered)) == sorted(map(repr, data))


@given(data=st.lists(st.integers(min_value=0, max_value=5), max_size=200))
def test_stability_matches_sorted(data: list[int]) -> None:
    # Tag each item with its input index; a stable sort by the value alone
    # must keep the indices ascending among equal values, exactly like sorted().
    tagged = list(enumerate(data))
    expected = sorted(tagged, key=lambda pair: pair[1])
    assert inlet_sort(tagged, key=lambda pair: pair[1]) == expected


@given(data=st.lists(_integers, max_size=300))
@settings(max_examples=100)
def test_inplace_matches_and_keeps_identity(data: list[int]) -> None:
    expected = sorted(data)
    original = data
    inlet_sort_inplace(data)
    assert data is original
    assert data == expected
