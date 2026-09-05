"""Command-line interface for Inlet Sort."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable, Sequence

from .sort import inlet_sort


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="inlet-sort",
        description="Sort lines of text or numbers with Inlet Sort.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="File to read (default: stdin).",
    )
    parser.add_argument(
        "-n",
        "--numeric",
        action="store_true",
        help="Parse each line as a number (int, then float).",
    )
    parser.add_argument(
        "-r",
        "--reverse",
        action="store_true",
        help="Sort in descending order.",
    )
    parser.add_argument(
        "-u",
        "--unique",
        action="store_true",
        help="Drop adjacent duplicates after sorting.",
    )
    args = parser.parse_args(argv)

    try:
        lines = list(_read_lines(args.path))
    except OSError as exc:
        print(f"inlet-sort: {exc}", file=sys.stderr)
        return 1

    if args.numeric:
        try:
            values: list[object] = [_parse_number(line) for line in lines]
        except ValueError as exc:
            print(f"inlet-sort: {exc}", file=sys.stderr)
            return 1
    else:
        values = list(lines)

    ordered = inlet_sort(values, reverse=args.reverse)
    if args.unique:
        ordered = _unique_adjacent(ordered)

    for item in ordered:
        print(item)
    return 0


def _read_lines(path: str | None) -> Iterable[str]:
    if path is None or path == "-":
        for line in sys.stdin:
            yield line.rstrip("\n")
        return
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            yield line.rstrip("\n")


def _parse_number(text: str) -> int | float:
    stripped = text.strip()
    try:
        return int(stripped, 10)
    except ValueError:
        try:
            return float(stripped)
        except ValueError as exc:
            raise ValueError(f"not a number: {text!r}") from exc


def _unique_adjacent(values: list[object]) -> list[object]:
    if not values:
        return values
    unique = [values[0]]
    for item in values[1:]:
        if item != unique[-1]:
            unique.append(item)
    return unique


if __name__ == "__main__":
    raise SystemExit(main())
