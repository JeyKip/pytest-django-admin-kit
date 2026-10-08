"""The rows of a changelist and the cells in them.

A cell is addressed by the name its column is configured with, never by the label
shown over it, and a row by its position. A cell is a rendered value, as the
``rendered`` module reads one, that also knows its column.
"""

from __future__ import annotations

from typing import Any, Callable, Iterator

from django.contrib.admin import ModelAdmin
from django.contrib.admin.utils import unquote
from django.db.models import Model
from django.urls import Resolver404, resolve
from playwright.sync_api import Locator

from .normalize import Normalizers
from .rendered import RenderedValue, display_text
from .urls import AdminUrls, model_admin


class Cell(RenderedValue):
    """One cell of a changelist row."""

    def __init__(
        self,
        element: Locator,
        column: str,
        check: Callable[[], None],
        normalizers: Normalizers,
        model_admin: ModelAdmin,
    ) -> None:
        super().__init__(element, check, normalizers, model_admin, column)
        self._column = column

    @property
    def column(self) -> str:
        """The configured name of the column the cell is in."""
        return self._column

    @property
    def empty_display(self) -> str:
        """The text the admin shows here for a value it has none of: the column's own, when
        it is a method or a callable that sets one, else the model admin's or the site's."""
        function = None if self.field is not None else self._display_function()
        if function is not None and hasattr(function, "empty_value_display"):
            return display_text(function.empty_value_display)
        return super().empty_display

    def _display_function(self) -> Any:
        """What the admin calls to render the column, looked up as the admin looks it up: a
        callable in ``list_display``, then the model admin's attribute, then the model's."""
        for entry in self._model_admin.list_display:
            if callable(entry) and getattr(entry, "__name__", None) == self._column:
                return entry
        if hasattr(self._model_admin, self._column):
            return getattr(self._model_admin, self._column)
        return getattr(self._model_admin.model, self._column, None)


class Row:
    """One row of a changelist, indexable by column name or position.

    The columns are the ones the changelist had when the row was read. A project whose
    ``list_display`` changes with the query string reads its rows again after filtering.
    """

    def __init__(
        self,
        element: Locator,
        index: int,
        columns: list[str],
        model: type[Model],
        urls: AdminUrls,
        check: Callable[[], None],
        normalizers: Normalizers,
    ) -> None:
        self._element = element
        self._index = index
        self._columns = columns
        self._model = model
        self._urls = urls
        self._check = check
        self._normalizers = normalizers

    @property
    def index(self) -> int:
        """The row's 0-based position in the changelist.

        The row is that position, not a record: every read goes to whichever row the page
        shows there now, so once the changelist is filtered or sorted it may be another one.
        """
        return self._index

    @property
    def native(self) -> Locator:
        """The row element, unwrapped, for anything the package does not model."""
        return self._element

    @property
    def object(self) -> Any:
        """The instance behind the row, where the changelist links to its change page.

        ``None`` for a row without such a link, as under ``list_display_links = None``.
        The database is asked each time, so the instance is as it is stored now.
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

    @property
    def _cells(self) -> list[Cell]:
        self._check()
        # The row's own cells line up with the columns by position once the
        # checkbox Django adds for actions is skipped, as the headers skip its
        # header cell.
        cells = self._element.locator(":scope > th, :scope > td").all()
        cells = [cell for cell in cells if "action-checkbox" not in _classes(cell)]
        admin = model_admin(self._urls.site, self._model)
        return [
            Cell(cell, column, self._check, self._normalizers, admin)
            for cell, column in zip(cells, self._columns)
        ]


def _classes(element: Locator) -> list[str]:
    return (element.get_attribute("class") or "").split()
