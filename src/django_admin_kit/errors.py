"""The validation errors a create or edit form shows after the admin rejected it.

The admin shows them at three levels, and each is read on its own: the summary
notice above the form, the errors of the form as a whole, and the errors of each field.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from playwright.sync_api import Locator

from .rendered import text_of

if TYPE_CHECKING:
    from .fields import Fields


class ValidationErrors:
    """The errors a form shows, read from the page each time they are asked for.

    ``form`` gives the form element and ``fields`` the form's fields; both fail when the
    browser no longer shows the page the form is on.
    """

    def __init__(self, form: Callable[[], Locator], fields: Callable[[], Fields]) -> None:
        self._form = form
        self._fields = fields

    @property
    def banner(self) -> str:
        """The notice the admin shows above a rejected form, or ``""`` when it shows none.

        Its wording depends on how many errors there are, so a test that only cares that
        the form was rejected asserts that it is there.
        """
        notice = self._form().locator("p.errornote")
        return text_of(notice) if notice.count() else ""

    @property
    def non_field(self) -> list[str]:
        """The errors of the form as a whole rather than of one field, in order.

        The notice is not one of them, though the admin shows them right under it.
        """
        # The form's own list is a direct child of the form's one div, which leaves out
        # the lists of the inline formsets next to it.
        items = self._form().locator(":scope > div > ul.errorlist.nonfield > li")
        return [text_of(item) for item in items.all()]

    @property
    def fields(self) -> dict[str, list[str]]:
        """The errors of each field that has any, by field name, in the order the admin
        presents the fields. One field's errors are read from it: ``field.errors``."""
        return {name: errors for name, field in self._fields().items() if (errors := field.errors)}

    def __bool__(self) -> bool:
        return bool(self.banner or self.non_field or self.fields)

    def __repr__(self) -> str:
        return (
            f"ValidationErrors(banner={self.banner!r}, non_field={self.non_field!r}, "
            f"fields={self.fields!r})"
        )
