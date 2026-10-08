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
    from django.db.models import Field
    from playwright.sync_api import Locator

    from .rendered import RenderedValue

Rule = Callable[["RenderedValue"], Any]

_ICONS = {"True": True, "False": False, "None": None}


def boolean(rendered: RenderedValue) -> Any:
    """A boolean the admin draws as an icon, read from the icon's ``alt``: ``True``,
    ``False``, or ``None`` for a nullable boolean that has no value."""
    return _ICONS[_icon(rendered).get_attribute("alt") or ""]


def empty(rendered: RenderedValue) -> Any:
    """A value the admin has none of, as the text it shows in its place."""
    return rendered.text


def link(rendered: RenderedValue) -> Any:
    """A value the admin renders as links, as their text; the links are in ``links``."""
    return rendered.text


def date(rendered: RenderedValue) -> Any:
    """A date, as the text the project's formats render."""
    return rendered.text


def datetime(rendered: RenderedValue) -> Any:
    """A date and time, as the text the project's formats render."""
    return rendered.text


def time(rendered: RenderedValue) -> Any:
    """A time of day, as the text the project's formats render."""
    return rendered.text


def number(rendered: RenderedValue) -> Any:
    """A number, as the text the project's formats render."""
    return rendered.text


def choice(rendered: RenderedValue) -> Any:
    """A value from a fixed set of choices, as the label the admin shows for it."""
    return rendered.text


def text(rendered: RenderedValue) -> Any:
    """Anything else, as its text."""
    return rendered.text


DEFAULTS: dict[str, Rule] = {
    "boolean": boolean,
    "empty": empty,
    "link": link,
    "date": date,
    "datetime": datetime,
    "time": time,
    "number": number,
    "choice": choice,
    "text": text,
}
"""The default rule for each kind, by the name a project replaces it under."""


class Normalizers:
    """The rule for each kind of value: the defaults, with the project's replacements."""

    def __init__(self, replaced: Mapping[str, Rule] | None = None) -> None:
        self._rules = {**DEFAULTS, **(replaced or {})}

    def read(self, rendered: RenderedValue) -> Any:
        """The value of ``rendered``, read by the rule for its kind."""
        return self._rules[_kind(rendered)](rendered)


def _kind(rendered: RenderedValue) -> str:
    """The kind of ``rendered``: by the model field behind it where it has one, then by what
    the admin drew."""
    # The admin marks a value it has none of only by the text it shows instead.
    if rendered.text == rendered.empty_display:
        return "empty"
    field = rendered.field
    if field is not None:
        # The admin shows a field with choices as their labels, whatever the field's class.
        if field.choices:
            return "choice"
        kind = _field_kind(field)
        if kind is not None:
            return kind
    if _draws_a_boolean(rendered):
        return "boolean"
    if rendered.links:
        return "link"
    return "text"


def _field_kind(field: Field) -> str | None:
    """The kind of the most specific class ``field`` is that has one, so a date-time field,
    which is also a date field, is a date-time."""
    # Imported here: this module loads at pytest startup, with the settings.
    from django.db import models

    kinds = {
        models.BooleanField: "boolean",
        models.DateTimeField: "datetime",
        models.DateField: "date",
        models.TimeField: "time",
        models.IntegerField: "number",
        models.DecimalField: "number",
        models.FloatField: "number",
    }
    return next((kinds[cls] for cls in type(field).__mro__ if cls in kinds), None)


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
