"""The object the ``admin_ui`` fixture yields.

Login builds the session in Django and hands the browser the resulting cookie. It
never types a password, because passwords are stored irreversibly and a test handed an
arbitrary user has no way to know one. A user created with ``set_unusable_password()``
has no password at all and must still be able to log in.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from django.conf import settings
from django.test import Client

from .browser import SessionCookie
from .urls import AdminUrls


class AdminSession:
    """One test's view of the admin: who is logged in, and where things live."""

    def __init__(self, context: Any, urls: AdminUrls, base_url: str) -> None:
        self._context = context
        self._urls = urls
        self._base_url = base_url

    @property
    def native(self) -> Any:
        """The browsing context, unwrapped, for anything the package does not model."""
        return self._context

    @property
    def url(self) -> AdminUrls:
        """Admin URLs resolved through the site under test, as paths."""
        return self._urls

    def absolute(self, path: str) -> str:
        """A path against the live server.

        The package navigates absolutely rather than setting the context's
        ``base_url``, which belongs to the project: a test suite already using
        ``--base-url`` for its own pages keeps it, and neither of us can break the
        other.
        """
        return urljoin(self._base_url, path)

    def login(self, user: Any) -> None:
        """Log in as ``user`` without knowing or needing a password.

        Calling it again replaces the session rather than adding a second one, so
        switching users mid-test works.
        """
        client = Client()
        client.force_login(user)
        cookie = SessionCookie(
            name=settings.SESSION_COOKIE_NAME,
            value=client.cookies[settings.SESSION_COOKIE_NAME].value,
        )
        self.logout()
        self._context.add_cookies([cookie.as_playwright(self._base_url)])

    def logout(self) -> None:
        """Return the browser to anonymous by dropping its cookies."""
        self._context.clear_cookies()
