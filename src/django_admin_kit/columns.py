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

    def __init__(
        self, name: str, shown: Callable[[], Page], follow: Callable[[Locator], bool]
    ) -> None:
        self._name = name
        self._shown = shown
        self._follow = follow

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

    def make_primary_sort(self, direction: SortDirection | str = SortDirection.ASCENDING) -> None:
        """Make the column the first one the changelist is sorted by, in ``direction``.

        The columns sorted before keep their order after it. This clicks the header, which
        flips a column that is already sorted, then the arrow when the direction came out wrong,
        so it takes one or two page loads, and none when the column is already first in that
        direction. This same page then reads the results.

        ``direction`` is a ``SortDirection`` or its string, ``"asc"`` or ``"desc"``; anything
        else raises ``ValueError``. A column the user can't sort by raises ``LookupError``. If
        the admin sends the browser elsewhere, such as to the login page after the session
        ended, the page stands for where it landed and reports it as ``denied`` or
        ``redirected``.
        """
        wanted = _direction(direction)
        cell = self._sortable_cell()
        state = _sort_state(cell)
        if state == (wanted, 1):
            return
        if state is not None and state[1] == 1:
            self._follow(cell.locator(".sortoptions a.toggle"))
            return
        if self._follow(cell.locator("div.text a")) and self.sort_direction is not wanted:
            self._follow(self.native.locator(".sortoptions a.toggle"))

    def set_sort_direction(self, direction: SortDirection | str) -> None:
        """Sort the column in ``direction`` and keep its place among the sorted columns.

        This clicks the arrow when the direction differs, and nothing when it is already
        ``direction``. This same page then reads the results. A column that isn't sorted has no
        place to keep, so it raises ``LookupError``: Django adds a column only as the first one,
        which ``make_primary_sort`` does.

        ``direction`` is checked as for ``make_primary_sort``, and so are a column the user
        can't sort by and a page the admin sends elsewhere.
        """
        wanted = _direction(direction)
        cell = self._sortable_cell()
        state = _sort_state(cell)
        if state is None:
            sign = "-" if wanted is SortDirection.DESCENDING else ""
            raise LookupError(
                f"The column {self._name!r} is not sorted, so it has no direction to set. "
                f"Sort by it with make_primary_sort({wanted.value!r}), which puts it first and "
                "keeps the other sorted columns after it, or with "
                f"page.sort({sign + self._name!r}, ...), which sorts by exactly the columns given."
            )
        if state[0] is not wanted:
            self._follow(cell.locator(".sortoptions a.toggle"))

    def remove_from_sort(self) -> None:
        """Take the column out of the sort, which the other sorted columns keep in their order.

        This clicks the header's remove link, and nothing when the column isn't sorted. This
        same page then reads the results. Once no column is sorted, the headers mark none, and
        Django orders the records by the admin's default ordering again from 5.2, and before
        that by their primary key alone, newest first.

        A column the user can't sort by raises ``LookupError``, and a page the admin sends
        elsewhere is reported as for ``make_primary_sort``.
        """
        cell = self._sortable_cell()
        if _sort_state(cell) is not None:
            # The admin shows the link only while the pointer is over the header, as a user's is.
            cell.hover()
            self._follow(cell.locator(".sortoptions a.sortremove"))

    def _sortable_cell(self) -> Locator:
        cell = self.native
        if not _sortable(cell):
            raise LookupError(f"The column {self._name!r} cannot be sorted.")
        return cell

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


def _direction(direction: SortDirection | str) -> SortDirection:
    """``direction`` as a member, or ``ValueError`` when it names no direction."""
    try:
        return SortDirection(direction)
    except ValueError:
        raise ValueError(f"{direction!r} is not a sort direction. Use 'asc' or 'desc'.") from None
