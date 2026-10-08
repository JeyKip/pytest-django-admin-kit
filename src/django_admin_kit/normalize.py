"""How the text of a rendered value becomes its value.

Each kind of value has a rule, a callable that takes the rendered value and returns what a
test reads. The package picks the rule for a value, so a rule reads one kind and never has to
tell the kinds apart. Every rule has a default here, and a project replaces any of them in its
settings.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Callable, Mapping

if TYPE_CHECKING:
    from playwright.sync_api import Locator

    from .rendered import RenderedValue

Rule = Callable[["RenderedValue"], Any]

_ICONS = {"True": True, "False": False, "None": None}


def boolean(rendered: RenderedValue) -> Any:
    """A boolean the admin draws as an icon, read from the icon's ``alt``: ``True``,
    ``False``, or ``None`` for a nullable boolean that has no value."""
    return _ICONS[_icon(rendered).get_attribute("alt") or ""]


def text(rendered: RenderedValue) -> Any:
    """Anything else, as its text."""
    return rendered.text


DEFAULTS: dict[str, Rule] = {"boolean": boolean, "text": text}
"""The default rule for each kind, by the name a project replaces it under."""


class Normalizers:
    """The rule for each kind of value: the defaults, with the project's replacements."""

    def __init__(self, replaced: Mapping[str, Rule] | None = None) -> None:
        self._rules = {**DEFAULTS, **(replaced or {})}

    def read(self, rendered: RenderedValue) -> Any:
        """The value of ``rendered``, read by the rule for its kind."""
        kind = "boolean" if _draws_a_boolean(rendered) else "text"
        return self._rules[kind](rendered)


def _icon(rendered: RenderedValue) -> Locator:
    return rendered.native.locator("img[alt]")


def _draws_a_boolean(rendered: RenderedValue) -> bool:
    """Whether the admin drew nothing but one of its boolean icons."""
    icon = _icon(rendered)
    if rendered.text or icon.count() != 1:
        return False
    return (icon.get_attribute("alt") or "") in _ICONS


def integer(rendered: str) -> int:
    """A whole number as the admin renders one, grouped or not.

    Grouping is the only thing a locale adds to an integer, so dropping everything that
    is not a digit reads it back under any separator.
    """
    return int(re.sub(r"\D", "", rendered))
