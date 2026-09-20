"""A value as the admin rendered it, wherever it stands: in a changelist cell or in a
form field the user may only read.

What such a value holds is read from the document's own text, so the admin's styling
never changes it, and the links it renders are kept next to it.
"""

from __future__ import annotations

from functools import cached_property
from typing import Any
from urllib.parse import SplitResult, urlsplit

from playwright.sync_api import Locator

from . import normalize


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
    """One value the admin rendered, read from the element that holds it."""

    def __init__(self, element: Locator) -> None:
        self._element = element

    @property
    def native(self) -> Locator:
        """The element, unwrapped, for anything the package does not model."""
        return self._element

    @cached_property
    def text(self) -> str:
        """What the document shows, with its whitespace collapsed."""
        return " ".join((self._element.text_content() or "").split())

    @cached_property
    def value(self) -> Any:
        """What is shown, normalized: the text, unless the admin drew an icon."""
        return normalize.normalize(self)

    @cached_property
    def links(self) -> list[Link]:
        """The links rendered, in order; ``[]`` when there is none."""
        return [
            Link(" ".join((a.text_content() or "").split()), a.get_attribute("href") or "")
            for a in self._element.locator("a[href]").all()
        ]
