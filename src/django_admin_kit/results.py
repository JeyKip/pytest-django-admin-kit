"""The outcome of submitting an admin form.

A result says whether the admin accepted the submission and where it sent the browser.
Anything shown on the page, such as fields, errors and messages, is read from
``result.page``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pages import AdminPage


class SubmissionResult:
    """The outcome of one form submission."""

    def __init__(self, page: AdminPage, redirected: bool) -> None:
        self._page = page
        self._redirected = redirected

    @property
    def page(self) -> AdminPage:
        """The page the browser shows after the submission.

        It is the submitted page object itself if the browser stayed on that page, and a
        new page object otherwise.
        """
        return self._page

    @property
    def success(self) -> bool:
        """Whether the admin accepted the submission.

        Django redirects after a successful save and shows the form again when it rejects
        one, so this is whether a redirect happened.
        """
        return self._redirected

    def redirected_to(self, url: str) -> bool:
        """Whether the admin redirected the browser to ``url``, a path such as
        ``admin_ui.url.list(Product)``.

        A rejected form is shown again at its own URL without a redirect, so it is never
        redirected to that URL.
        """
        return self._redirected and self._page.destination == url
