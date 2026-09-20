"""How the text of a rendered value becomes its value.

Rules are tried in the order of the table and the first one that answers wins. Each
rule looks at what was rendered and either returns the value or passes with
``NOT_HANDLED``. The last rule, ``text``, always answers, so everything has a value.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from .rendered import RenderedValue

NOT_HANDLED = object()

_ICONS = {"True": True, "False": False, "None": None}


def boolean(rendered: RenderedValue) -> Any:
    """A boolean the admin draws as an icon, whose ``alt`` names the value."""
    icon = rendered.native.locator("img[alt]")
    if rendered.text or icon.count() != 1:
        return NOT_HANDLED
    return _ICONS.get(icon.get_attribute("alt") or "", NOT_HANDLED)


def text(rendered: RenderedValue) -> Any:
    return rendered.text


Rule = Callable[["RenderedValue"], Any]

RULES: dict[str, Rule] = {"boolean": boolean, "text": text}


def normalize(rendered: RenderedValue) -> Any:
    for rule in RULES.values():
        value = rule(rendered)
        if value is not NOT_HANDLED:
            return value
    raise AssertionError(f"no rule answered for {rendered.text!r}")


def integer(rendered: str) -> int:
    """A whole number as the admin renders one, grouped or not.

    Grouping is the only thing a locale adds to an integer, so dropping everything that
    is not a digit reads it back under any separator.
    """
    return int(re.sub(r"\D", "", rendered))
