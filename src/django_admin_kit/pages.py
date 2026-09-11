"""Admin pages after they have been opened: where the browser ended up, and whether
it got in.

The admin answers a page request in more ways than a status code shows. A user who
is not logged in or not staff is redirected to the login page. A staff user without
permission for a model is refused in place with a 403. A user who has permission but
asks for an object that does not exist is sent to the index with a message, and a
URL the admin does not serve is a 404. One resolver turns the requested path, the
final path and the status into ``works``, ``denied``, ``missing`` and ``redirected``,
so that reading is written once.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from playwright.sync_api import Page

from .urls import AdminUrls


class AdminPage:
    """One opened admin page."""

    def __init__(self, page: Page, status_code: int, requested: str, urls: AdminUrls) -> None:
        self._page = page
        self._status_code = status_code
        self._requested = requested
        self._urls = urls

    @property
    def native(self) -> Page:
        """The browser page, unwrapped, for anything the package does not model."""
        return self._page

    @property
    def status_code(self) -> int:
        """The status of the response the browser ended up on, after any redirects."""
        return self._status_code

    @property
    def destination(self) -> str:
        """The path the browser ended up on, comparable with ``admin_ui.url``.

        Query string and fragment are dropped, so a redirect to the login page compares
        equal to ``admin_ui.url.login()`` whatever ``next`` it carries.
        """
        return urlsplit(self._page.url).path

    @property
    def redirected(self) -> bool:
        """Ended up somewhere other than the page asked for."""
        return self.destination != self._requested

    @property
    def works(self) -> bool:
        """Loaded where it was asked for."""
        return self._status_code == 200 and not self.redirected

    @property
    def denied(self) -> bool:
        """Refused, whether by redirect to the login page or in place."""
        return self._status_code == 403 or self.destination == self._urls.login()

    @property
    def missing(self) -> bool:
        """Not there: a URL the admin does not serve, or an object that does not exist.

        The admin reports a missing object to a user with permission by redirecting
        to the index with a message, so a redirect there is read as missing. A user
        without permission is refused before the object is looked up. The one other
        page that redirects to the index is the login page, when the user is already
        logged in; that is a plain redirect.
        """
        if self._status_code == 404:
            return True
        return (
            self.redirected
            and self.destination == self._urls.index()
            and self._requested != self._urls.login()
        )
