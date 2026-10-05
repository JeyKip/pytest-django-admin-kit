"""The validation errors a create or edit form shows after the admin rejected it.

The admin shows them at several levels, and each is read on its own: the summary
notice above the form is never mistaken for an error of the form itself.
"""

from __future__ import annotations

from typing import Callable

from playwright.sync_api import Locator

from .rendered import text_of


class ValidationErrors:
    """The errors a form shows, read from the page each time they are asked for.

    ``form`` gives the form element, and fails when the browser no longer shows the
    page the form is on.
    """

    def __init__(self, form: Callable[[], Locator]) -> None:
        self._form = form

    @property
    def banner(self) -> str:
        """The notice the admin shows above a rejected form, or ``""`` when it shows none.

        Its wording depends on how many errors there are, so a test that only cares that
        the form was rejected asserts that it is there.
        """
        notice = self._form().locator("p.errornote")
        return text_of(notice) if notice.count() else ""

    def __bool__(self) -> bool:
        return bool(self.banner)

    def __repr__(self) -> str:
        return f"ValidationErrors(banner={self.banner!r})"
