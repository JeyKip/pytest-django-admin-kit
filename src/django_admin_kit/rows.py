"""The rows of a changelist and the cells in them.

A cell is addressed by the name its column is configured with, never by the label
shown over it, and a row by its position. What a cell holds is read from the
document's own text, so the admin's styling never changes a value.
"""

from __future__ import annotations

from functools import cached_property
from typing import Any, Iterator
from urllib.parse import SplitResult, urlsplit

from django.contrib.admin.utils import unquote
from django.db.models import Model
from django.urls import Resolver404, resolve
from playwright.sync_api import Locator

from . import normalize
from .urls import AdminUrls


class Link:
    """One link in a cell: its text, and its ``href`` exactly as rendered, split.

    ``href`` is a ``SplitResult``, so its parts are there by name: ``path`` to compare
    against ``admin_ui.url``, ``query`` for what the admin added to keep a filter. A
    link compares equal to another link and to a ``(text, href)`` pair, as a tuple or a
    list, with ``href`` given either as a string or already split.
    """

    def __init__(self, text: str, href: str | SplitResult) -> None:
        self._text = text
        self._href = urlsplit(href) if isinstance(href, str) else href

    @property
    def text(self) -> str:
        return self._text

    @property
    def href(self) -> SplitResult:
        return self._href

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Link):
            return (self._text, self._href) == (other._text, other._href)
        if isinstance(other, (tuple, list)) and len(other) == 2:
            text, href = other
            if isinstance(text, str) and isinstance(href, (str, SplitResult)):
                return self == Link(text, href)
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self._text, self._href))

    def __repr__(self) -> str:
        return f"Link({self._text!r}, {self._href.geturl()!r})"


class Cell:
    """One cell of a changelist row."""

    def __init__(self, element: Locator, column: str) -> None:
        self._element = element
        self._column = column

    @property
    def column(self) -> str:
        """The configured name of the column the cell is in."""
        return self._column

    @property
    def native(self) -> Locator:
        """The cell element, unwrapped, for anything the package does not model."""
        return self._element

    @cached_property
    def text(self) -> str:
        """What the document shows in the cell, with its whitespace collapsed."""
        return " ".join((self._element.text_content() or "").split())

    @cached_property
    def value(self) -> Any:
        """What the cell shows, normalized: its text, unless the admin drew an icon."""
        return normalize.normalize(self)

    @cached_property
    def links(self) -> list[Link]:
        """The links the cell renders, in order; ``[]`` for a cell without one."""
        return [
            Link(" ".join((a.text_content() or "").split()), a.get_attribute("href") or "")
            for a in self._element.locator("a[href]").all()
        ]


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
