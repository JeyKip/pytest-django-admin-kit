"""A value as the admin rendered it, wherever it stands: in a changelist cell or in a
form field the user may only read.

What such a value holds is read from the document's own text, so the admin's styling
never changes it, and the links it renders are kept next to it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable
from urllib.parse import SplitResult, urlsplit

from django.contrib.admin import ModelAdmin
from django.contrib.admin.utils import NotRelationField, get_fields_from_path
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Field
from django.utils.html import strip_tags
from playwright.sync_api import Locator

if TYPE_CHECKING:
    from .normalize import Normalizers


class Link:
    """One link in a rendered value: its text, and its ``href`` exactly as rendered, split.

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


class RenderedValue:
    """One value the admin rendered, read from the element that holds it.

    ``check`` is run before every read, and fails when the browser no longer shows the
    page the value is on. ``normalizers`` read its value, by what stands behind it: the
    ``name`` the admin renders it under, on a page ``model_admin`` draws.
    """

    def __init__(
        self,
        element: Locator,
        check: Callable[[], None],
        normalizers: Normalizers,
        model_admin: ModelAdmin,
        name: str,
    ) -> None:
        self._element = element
        self._check = check
        self._normalizers = normalizers
        self._model_admin = model_admin
        self._name = name

    @property
    def native(self) -> Locator:
        """The element, unwrapped, for anything the package does not model."""
        return self._element

    @property
    def field(self) -> Field | None:
        """The model field the admin rendered the value from, or ``None``, as for a method."""
        return _model_field(self._model_admin.model, self._name)

    @property
    def empty_display(self) -> str:
        """The text the admin shows here for a value it has none of: the model admin's, which
        falls back to the site's."""
        return display_text(self._model_admin.get_empty_value_display())

    @property
    def text(self) -> str:
        """What the document shows, with its whitespace collapsed."""
        self._check()
        return text_of(self._element)

    @property
    def value(self) -> Any:
        """What is shown, read by the rule for its kind: by default the text, or a boolean
        where the admin drew one as an icon."""
        self._check()
        return self._normalizers.read(self)

    @property
    def links(self) -> list[Link]:
        """The links rendered, in order; ``[]`` when there is none."""
        self._check()
        return [
            Link(text_of(a), a.get_attribute("href") or "")
            for a in self._element.locator("a[href]").all()
        ]


def text_of(element: Locator) -> str:
    """The document's text inside ``element``, with its whitespace collapsed."""
    return " ".join((element.text_content() or "").split())


def display_text(display: str) -> str:
    """``display`` as the page shows it: without markup, its whitespace collapsed."""
    return " ".join(strip_tags(str(display)).split())


def _model_field(model: type[Any], name: str) -> Field | None:
    """The model field the admin renders under ``name``, or ``None`` when it renders something
    else there, such as a method.

    The admin looks a name up as a field first, following a path such as ``category__name``,
    and only then as a callable or a method, so a name that is a field is always that field.
    """
    try:
        return get_fields_from_path(model, name)[-1]
    except (FieldDoesNotExist, NotRelationField):
        return None
