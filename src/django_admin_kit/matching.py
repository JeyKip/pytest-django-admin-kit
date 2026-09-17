"""Matching changelist rows against patterns, and saying what did not match.

A failed match raises ``AssertionError`` carrying the expected pattern and the rows
actually shown, so that a test reads the whole picture under the line that failed, the
way any assertion helper reports.
"""

from __future__ import annotations

from typing import Any, Sequence

from .rows import Row


def matches(pattern: Sequence[Any], row: Row) -> bool:
    """Whether one row pattern, a cell pattern per column, describes ``row``."""
    return len(pattern) == len(row) and all(
        expected == cell.value for expected, cell in zip(pattern, row)
    )


def contains(rows: Sequence[Row], pattern: Sequence[Any]) -> bool:
    """``True`` when some row matches ``pattern``; otherwise the failure, raised."""
    __tracebackhide__ = True
    if any(matches(pattern, row) for row in rows):
        return True
    raise AssertionError(_no_match(pattern, rows))


def _no_match(pattern: Sequence[Any], rows: Sequence[Row]) -> str:
    shown = [f"    {tuple(cell.value for cell in row)!r}" for row in rows] or ["    (none)"]
    lines = ["Expected row:", f"    {pattern!r}", "", "No matching row found.", "", "Actual rows:"]
    return "\n".join(lines + shown)
