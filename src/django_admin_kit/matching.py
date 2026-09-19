"""Matching changelist rows against patterns, and saying what did not match.

A failed match raises ``AssertionError`` carrying the expected pattern and the rows
actually shown, so that a test reads the whole picture under the line that failed, the
way any assertion helper reports.
"""

from __future__ import annotations

from typing import Any, Sequence

from .rows import Cell, Link, Row


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


def contains(rows: Sequence[Row], pattern: Any) -> bool:
    """``True`` when some row matches ``pattern``; otherwise the failure, raised."""
    __tracebackhide__ = True
    if any(matches(pattern, row) for row in rows):
        return True
    raise AssertionError(_no_match(pattern, rows))


def _no_match(pattern: Any, rows: Sequence[Row]) -> str:
    shown = [f"    {_shown(row, pattern)!r}" for row in rows] or ["    (none)"]
    expected = f"    {_described(pattern)!r}"
    lines = ["Expected row:", expected, "", "No matching row found.", "", "Actual rows:"]
    return "\n".join(lines + shown)


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
    if isinstance(expected, (tuple, list)):
        return all(isinstance(item, Link) for item in expected)
    return isinstance(expected, Link)
