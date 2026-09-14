"""The rows of a changelist and the cells in them.

A cell is addressed by the name its column is configured with, never by the label
shown over it, and a row by its position. What a cell holds is read from the
document's own text, so the admin's styling never changes a value.
"""

from __future__ import annotations

from functools import cached_property

from playwright.sync_api import Locator


class Cell:
    """One cell of a changelist row."""

    def __init__(self, element: Locator) -> None:
        self._element = element

    @property
    def native(self) -> Locator:
        """The cell element, unwrapped, for anything the package does not model."""
        return self._element

    @cached_property
    def text(self) -> str:
        """What the document shows in the cell, with its whitespace collapsed."""
        return " ".join((self._element.text_content() or "").split())

    @property
    def value(self) -> str:
        """The cell's meaning, which for now is its text."""
        return self.text


class Row:
    """One row of a changelist, indexable by column name or position."""

    def __init__(self, element: Locator, index: int, columns: list[str]) -> None:
        self._element = element
        self._index = index
        self._columns = columns

    @property
    def index(self) -> int:
        """The row's 0-based position in the changelist."""
        return self._index

    @property
    def native(self) -> Locator:
        """The row element, unwrapped, for anything the package does not model."""
        return self._element

    def __getitem__(self, key: int | str) -> Cell:
        if isinstance(key, int):
            return self._cells[key]
        try:
            return self._cells[self._columns.index(key)]
        except ValueError:
            raise KeyError(
                f"The row has no column named {key!r}. Columns: "
                f"{', '.join(repr(name) for name in self._columns)}."
            ) from None

    @cached_property
    def _cells(self) -> list[Cell]:
        # The row's own cells line up with the columns by position once the
        # checkbox Django adds for actions is skipped, as the headers skip its
        # header cell.
        cells = self._element.locator(":scope > th, :scope > td").all()
        return [Cell(cell) for cell in cells if "action-checkbox" not in _classes(cell)]


def _classes(element: Locator) -> list[str]:
    return (element.get_attribute("class") or "").split()
