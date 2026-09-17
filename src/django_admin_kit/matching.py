"""Matching changelist rows against patterns, and saying what did not match.

A failed match raises ``AssertionError`` carrying the expected pattern and the rows
actually shown, so that a test reads the whole picture under the line that failed, the
way any assertion helper reports.
"""

from __future__ import annotations

from typing import Any, Sequence
from urllib.parse import SplitResult

from .rows import Cell, Link, Row


def matches(pattern: Sequence[Any], row: Row) -> bool:
    """Whether one row pattern, a cell pattern per column, describes ``row``."""
    return len(pattern) == len(row) and all(
        _cell_matches(expected, cell) for expected, cell in zip(pattern, row)
    )


def _cell_matches(expected: Any, cell: Cell) -> bool:
    # A link pair describes a cell that renders that one link; a list or tuple of
    # pairs, the cell's links exactly. Either may also be the value itself, when a
    # project's own rule produces such a value, so a pair that is no link of the cell
    # is still compared to what the cell shows.
    if _is_link(expected) and cell.links == [expected]:
        return True
    if _is_links(expected) and cell.links == list(expected):
        return True
    # `==` may return something other than a bool for an arbitrary value; only its
    # truth decides the match.
    return bool(expected == cell.value)


def _is_link(pattern: Any) -> bool:
    if isinstance(pattern, Link):
        return True
    return (
        isinstance(pattern, (tuple, list))
        and len(pattern) == 2
        and isinstance(pattern[0], str)
        and isinstance(pattern[1], (str, SplitResult))
    )


def _is_links(pattern: Any) -> bool:
    return isinstance(pattern, (tuple, list)) and all(_is_link(item) for item in pattern)


def contains(rows: Sequence[Row], pattern: Sequence[Any]) -> bool:
    """``True`` when some row matches ``pattern``; otherwise the failure, raised."""
    __tracebackhide__ = True
    if any(matches(pattern, row) for row in rows):
        return True
    raise AssertionError(_no_match(pattern, rows))


def _no_match(pattern: Sequence[Any], rows: Sequence[Row]) -> str:
    shown = [f"    {_shown(row, pattern)!r}" for row in rows] or ["    (none)"]
    lines = ["Expected row:", f"    {pattern!r}", "", "No matching row found.", "", "Actual rows:"]
    return "\n".join(lines + shown)


def _shown(row: Row, pattern: Sequence[Any]) -> tuple[Any, ...]:
    # A row is shown as its values, except where the pattern asked about links: there
    # the cell's links are shown instead, so the two line up.
    shown = []
    for index, cell in enumerate(row):
        expected = pattern[index] if index < len(pattern) else None
        if _is_link(expected) or _is_links(expected):
            shown.append(cell.links)
        else:
            shown.append(cell.value)
    return tuple(shown)
