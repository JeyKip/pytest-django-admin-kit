"""One column of a changelist, as its header shows it.

A column is found by its name each time it is used, so the same object keeps working after the
page loads again, such as after a search.
"""

from __future__ import annotations

from typing import Callable

from playwright.sync_api import Locator, Page

from ._html import stripped_text


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

    def __repr__(self) -> str:
        return f"ChangelistColumn({self._name!r})"


def _sortable(cell: Locator) -> bool:
    """Whether the admin marks a changelist header cell as one the user can sort by."""
    return "sortable" in (cell.get_attribute("class") or "").split()
