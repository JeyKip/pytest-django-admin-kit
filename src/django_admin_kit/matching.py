"""Matching changelist rows against patterns, and saying what did not match.

A failed match raises ``AssertionError`` carrying the expected pattern and the rows
actually shown, so that a test reads the whole picture under the line that failed, the
way any assertion helper reports.
"""

from __future__ import annotations

from typing import Any, Sequence
from urllib.parse import SplitResult

from .rendered import Link
from .rows import Cell, Row


class _Named:
    """A value that prints as its name: a sentinel, or a callable shown in a failure."""

    def __init__(self, name: str) -> None:
        self._name = name

    def __repr__(self) -> str:
        return self._name


ANY = _Named("ANY")
"""A cell pattern any cell matches: the cell must exist, its contents do not matter."""

ANY_ROW = _Named("ANY_ROW")
"""A row pattern any row matches."""


def matches(pattern: Any, row: Row) -> bool:
    """Whether one row pattern describes ``row``: ``ANY_ROW``, a cell pattern per
    column, or cell patterns by column name, the columns left out unconstrained."""
    if pattern is ANY_ROW:
        return True
    if isinstance(pattern, dict):
        # An unknown name raises from the row, naming its columns: a misspelt
        # column is a mistake to see, not a row that happens not to match.
        return all(_cell_matches(expected, row, row[name]) for name, expected in pattern.items())
    return len(pattern) == len(row) and all(
        _cell_matches(expected, row, cell) for expected, cell in zip(pattern, row)
    )


def _cell_matches(expected: Any, row: Row, cell: Cell) -> bool:
    if expected is ANY:
        return True
    if callable(expected):
        # The test's own code: whatever it raises is its own bug to see.
        return bool(expected(row, cell))
    # A pattern describes the cell's links or its value, whichever it equals: one link
    # as the cell's only link, a list or tuple of links as all of them. Nothing is read
    # into a pattern's shape, so a project whose own rule puts links into the value
    # matches them the same way.
    if cell.links == [expected]:
        return True
    if isinstance(expected, (tuple, list)) and cell.links == list(expected):
        return True
    # `==` may return something other than a bool for an arbitrary value; only its
    # truth decides the match.
    return bool(expected == cell.value)


def contains(pattern: Any, rows: Sequence[Row]) -> bool:
    """``True`` when some row matches ``pattern``; otherwise the failure, raised."""
    __tracebackhide__ = True
    if any(matches(pattern, row) for row in rows):
        return True
    raise AssertionError(_no_match(pattern, rows))


def match(patterns: Any, rows: Sequence[Row]) -> bool:
    """``True`` when the rows are exactly ``patterns``, one row per pattern in order;
    otherwise the failure, raised."""
    __tracebackhide__ = True
    if not isinstance(patterns, (tuple, list)):
        raise TypeError(
            "match() takes a list or tuple of row patterns, one per row of the changelist; "
            f"got {patterns!r}. A single row is written as [row]."
        )
    if len(patterns) != len(rows):
        raise AssertionError(_wrong_count(patterns, rows))
    wrong = [
        index
        for index, (pattern, row) in enumerate(zip(patterns, rows))
        if not matches(pattern, row)
    ]
    if wrong:
        raise AssertionError(_wrong_rows(patterns, wrong, rows))
    return True


def _no_match(pattern: Any, rows: Sequence[Row]) -> str:
    expected = f"    {_described(pattern)!r}"
    lines = ["Expected row:", expected, "", "No matching row found.", "", "Actual rows:"]
    return "\n".join(lines + _shown_rows(rows, pattern))


def _wrong_count(patterns: Sequence[Any], rows: Sequence[Row]) -> str:
    lines = ["Expected rows:", *_described_rows(patterns), ""]
    lines.append(f"Expected {_count(len(patterns))}, found {len(rows)}.")
    return "\n".join([*lines, "", "Actual rows:", *_shown_rows(rows, None)])


def _wrong_rows(patterns: Sequence[Any], wrong: list[int], rows: Sequence[Row]) -> str:
    lines = ["Expected rows:", *_described_rows(patterns)]
    for index in wrong:
        lines += ["", f"Row {index} did not match:"]
        lines.append(f"    expected {_described(patterns[index])!r}")
        lines.append(f"    actual   {_shown(rows[index], patterns[index])!r}")
    return "\n".join([*lines, "", "Actual rows:", *_shown_rows(rows, None)])


def _count(number: int) -> str:
    return f"{number} row" if number == 1 else f"{number} rows"


def _described_rows(patterns: Sequence[Any]) -> list[str]:
    return [f"    {_described(pattern)!r}" for pattern in patterns] or ["    (none)"]


def _shown_rows(rows: Sequence[Row], pattern: Any) -> list[str]:
    return [f"    {_shown(row, pattern)!r}" for row in rows] or ["    (none)"]


def _described(pattern: Any) -> Any:
    # A callable prints as its name, since its repr says nothing a reader can use.
    if isinstance(pattern, dict):
        return {name: _described_cell(item) for name, item in pattern.items()}
    if isinstance(pattern, (tuple, list)):
        return type(pattern)(_described_cell(item) for item in pattern)
    return pattern


def _described_cell(expected: Any) -> Any:
    if callable(expected):
        return _Named(getattr(expected, "__name__", repr(expected)))
    return expected


def _shown(row: Row, pattern: Any) -> Any:
    # A row is shown the way the pattern addressed it: as its values in order, or by
    # the columns the pattern named; where the pattern asked about links, the cell's
    # links are shown instead, so the two line up.
    if isinstance(pattern, dict):
        return {name: _shown_cell(row[name], expected) for name, expected in pattern.items()}
    cells = pattern if isinstance(pattern, Sequence) else ()
    return tuple(
        _shown_cell(cell, cells[index] if index < len(cells) else None)
        for index, cell in enumerate(row)
    )


def _shown_cell(cell: Cell, expected: Any) -> Any:
    if _asks_for_links(expected):
        return cell.links
    return cell.value


def _asks_for_links(expected: Any) -> bool:
    # For display only: a pattern that is a link, a pair, or a list or tuple of them.
    if _is_link(expected):
        return True
    return isinstance(expected, (tuple, list)) and all(_is_link(item) for item in expected)


def _is_link(expected: Any) -> bool:
    if isinstance(expected, Link):
        return True
    return (
        isinstance(expected, (tuple, list))
        and len(expected) == 2
        and isinstance(expected[0], str)
        and isinstance(expected[1], (str, SplitResult))
    )
