"""The rows of a changelist and the cells in them.

A cell is addressed by the name its column is configured with, never by the label
shown over it, and a row by its position. A cell is a rendered value, as the
``rendered`` module reads one, that also knows its column.
"""

from __future__ import annotations

from functools import cached_property
from typing import Any, Iterator

from django.contrib.admin.utils import unquote
from django.db.models import Model
from django.urls import Resolver404, resolve
from playwright.sync_api import Locator

from .rendered import RenderedValue
from .urls import AdminUrls


class Cell(RenderedValue):
    """One cell of a changelist row."""

    def __init__(self, element: Locator, column: str) -> None:
        super().__init__(element)
        self._column = column

    @property
    def column(self) -> str:
        """The configured name of the column the cell is in."""
        return self._column


class Row:
    """One row of a changelist, indexable by column name or position."""

    def __init__(
        self,
        element: Locator,
        index: int,
        columns: list[str],
        model: type[Model],
        urls: AdminUrls,
    ) -> None:
        self._element = element
        self._index = index
        self._columns = columns
        self._model = model
        self._urls = urls

    @property
    def index(self) -> int:
        """The row's 0-based position in the changelist."""
        return self._index

    @property
    def native(self) -> Locator:
        """The row element, unwrapped, for anything the package does not model."""
        return self._element

    @cached_property
    def object(self) -> Any:
        """The instance behind the row, where the changelist links to its change page.

        ``None`` for a row without such a link, as under ``list_display_links = None``.
        """
        opts = self._model._meta
        for cell in self._cells:
            for link in cell.links:
                try:
                    match = resolve(link.href.path)
                except Resolver404:
                    continue
                if (
                    match.namespace == self._urls.site.name
                    and match.url_name == f"{opts.app_label}_{opts.model_name}_change"
                ):
                    return self._model._default_manager.get(pk=unquote(match.kwargs["object_id"]))
        return None

    def __len__(self) -> int:
        return len(self._cells)

    def __iter__(self) -> Iterator[Cell]:
        return iter(self._cells)

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
        cells = [cell for cell in cells if "action-checkbox" not in _classes(cell)]
        return [Cell(cell, column) for cell, column in zip(cells, self._columns)]


def _classes(element: Locator) -> list[str]:
    return (element.get_attribute("class") or "").split()
