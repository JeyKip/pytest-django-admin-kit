"""One column of a changelist, as its header shows it.

A column is found by its name each time it is used, so the same object keeps working after the
page loads again, such as after a search.

How a column is sorted is read from the marks Django puts on its header. Without a sort in the
URL, Django marks the columns of the admin's default ordering that it can match to a column, so
these follow the headers, and the rows show the real order.
"""

from __future__ import annotations

from enum import Enum
from typing import Callable

from playwright.sync_api import Locator, Page

from ._html import stripped_text


class SortDirection(str, Enum):
    """The direction a changelist column is sorted in.

    A member is its own word, so ``SortDirection.DESCENDING`` and ``"desc"`` are the same thing
    to compare.
    """

    ASCENDING = "asc"
    DESCENDING = "desc"


class ChangelistColumn:
    """One changelist column, read from its header cell each time it is used."""

    def __init__(self, name: str, shown: Callable[[], Page]) -> None:
        self._name = name
        self._shown = shown

    @property
    def name(self) -> str:
        """The name the admin is configured with, as ``page.columns`` lists it."""
        return self._name

    @property
    def label(self) -> str:
        """The label the header shows, as ``page.headers`` lists it."""
        return stripped_text(self.native.locator("div.text"))

    @property
    def native(self) -> Locator:
        """The header cell, unwrapped, for anything the package does not model."""
        cell = self._shown().locator(f'#result_list thead th[class~="column-{self._name}"]')
        if not cell.count():
            raise LookupError(f"The page no longer shows the column {self._name!r}.")
        return cell

    @property
    def sortable(self) -> bool:
        """Whether the user can sort by the column.

        This reads the page rather than ``ModelAdmin.sortable_by``, as
        ``page.sortable_columns`` does.
        """
        return _sortable(self.native)

    @property
    def sort_direction(self) -> SortDirection | None:
        """The direction the header shows the column sorted in, or ``None`` when it isn't
        sorted or can't be."""
        state = _sort_state(self.native)
        return state[0] if state else None

    @property
    def sort_priority(self) -> int | None:
        """The column's place among the sorted columns, ``1`` for the first one, or ``None``
        when it isn't sorted or can't be."""
        state = _sort_state(self.native)
        return state[1] if state else None

    def __repr__(self) -> str:
        return f"ChangelistColumn({self._name!r})"


def _sortable(cell: Locator) -> bool:
    """Whether the admin marks a changelist header cell as one the user can sort by."""
    return "sortable" in (cell.get_attribute("class") or "").split()


def _sort_state(cell: Locator) -> tuple[SortDirection, int] | None:
    """The direction and the priority a header cell shows, or ``None`` when it isn't sorted.

    Django shows the priority only while two or more columns are sorted, so a lone sorted
    column is the first.
    """
    classes = (cell.get_attribute("class") or "").split()
    if "sorted" not in classes:
        return None
    direction = SortDirection.DESCENDING if "descending" in classes else SortDirection.ASCENDING
    priority = cell.locator(".sortoptions .sortpriority")
    return direction, int(stripped_text(priority)) if priority.count() else 1
