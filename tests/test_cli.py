"""CLI tests for inlet-sort."""

from __future__ import annotations

from pathlib import Path

from inlet_sort.cli import main


def test_numeric_file_sort(tmp_path: Path, capsys) -> None:
    path = tmp_path / "nums.txt"
    path.write_text("10\n2\n2\n-1\n", encoding="utf-8")
    assert main([str(path), "--numeric"]) == 0
    assert capsys.readouterr().out.splitlines() == ["-1", "2", "2", "10"]


def test_reverse_unique_words(tmp_path: Path, capsys) -> None:
    path = tmp_path / "words.txt"
    path.write_text("pear\napple\npear\nbanana\n", encoding="utf-8")
    assert main([str(path), "--reverse", "--unique"]) == 0
    assert capsys.readouterr().out.splitlines() == ["pear", "banana", "apple"]


def test_bad_numeric_line(tmp_path: Path, capsys) -> None:
    path = tmp_path / "bad.txt"
    path.write_text("1\nnope\n", encoding="utf-8")
    assert main([str(path), "-n"]) == 1
    err = capsys.readouterr().err
    assert "not a number" in err


def test_missing_file() -> None:
    assert main(["/definitely/not/here.txt"]) == 1
