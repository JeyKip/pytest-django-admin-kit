"""Small readers of the admin's markup that several modules share.

The module is internal: its names may change in any release.
"""

from __future__ import annotations

from playwright.sync_api import Locator


def stripped_text(element: Locator) -> str:
    """The text inside ``element`` with the whitespace around it removed, or ``""`` when the
    page has no such element."""
    return (element.text_content() or "").strip() if element.count() else ""


def class_suffix(element: Locator, prefix: str) -> str:
    """The rest of the first class of ``element`` that starts with ``prefix``, such as
    ``"price"`` from ``column-price``."""
    classes = (element.get_attribute("class") or "").split()
    return next(c[len(prefix) :] for c in classes if c.startswith(prefix))
