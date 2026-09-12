"""The object the ``admin_ui`` fixture yields.

Login builds the session in Django and hands the browser the resulting cookie. It
never types a password, because passwords are stored irreversibly and a test handed an
arbitrary user has no way to know one. A user created with ``set_unusable_password()``
has no password at all and must still be able to log in.
"""

from __future__ import annotations

from typing import Any, TypeVar
from urllib.parse import urljoin

from django.conf import settings
from django.test import Client
from playwright.sync_api import BrowserContext

from .pages import AdminPage, IndexPage
from .urls import AdminUrls

_P = TypeVar("_P", bound=AdminPage)


class AdminSession:
    """One test's view of the admin: who is logged in, and where things live."""

    def __init__(self, context: BrowserContext, urls: AdminUrls, base_url: str) -> None:
        self._context = context
        self._urls = urls
        self._base_url = base_url

    @property
    def native(self) -> BrowserContext:
        """The browsing context, unwrapped, for anything the package does not model."""
        return self._context

    @property
    def url(self) -> AdminUrls:
        """Admin URLs resolved through the site under test, as paths."""
        return self._urls

    def absolute(self, path: str) -> str:
        """Turn an admin path into a full URL on the live server.

        The package navigates absolutely rather than setting the context's
        ``base_url``, which belongs to the project: a test suite already using
        ``--base-url`` for its own pages keeps it, and neither of us can break the
        other.
        """
        return urljoin(self._base_url, path)

    def login(self, user: Any, password: str | None = None) -> None:
        """Log in as ``user`` without knowing or needing a password.

        Calling it again replaces the session rather than adding a second one, so
        switching users mid-test works.

        With ``password``, the rendered login form is driven instead: the browser
        opens the login page, types what the user model identifies users by and the
        password, and submits. That is for tests whose subject is the login page. A
        wrong password leaves the browser on the form, with its error shown, and the
        session anonymous.
        """
        self.logout()

        if password is None:
            self._login_with_cookie(user)
        else:
            self._login_with_form(user, password)

    def _login_with_cookie(self, user: Any) -> None:
        client = Client()
        client.force_login(user)

        name = settings.SESSION_COOKIE_NAME
        self._context.add_cookies(
            [{"name": name, "value": client.cookies[name].value, "url": self._base_url}]
        )

    def _login_with_form(self, user: Any, password: str) -> None:
        page = self._context.new_page()
        page.goto(self.absolute(self._urls.login()))

        # The admin's form names the identity input `username` whatever the user
        # model calls the field; only the value it expects follows the model.
        page.locator('input[name="username"]').fill(user.get_username())
        page.locator('input[name="password"]').fill(password)
        with page.expect_response(lambda response: response.request.method == "POST"):
            page.locator('input[type="submit"]').click()
        page.wait_for_load_state()

    def logout(self) -> None:
        """Return the browser to anonymous by dropping its cookies."""
        self._context.clear_cookies()

    def open(self, path: str) -> AdminPage:
        """Open any admin path in a new page, including views the package does not
        model, and report how it went."""
        return self._open(path, AdminPage)

    def index(self) -> IndexPage:
        """Open the admin index."""
        return self._open(self._urls.index(), IndexPage)

    def _open(self, path: str, page_class: type[_P]) -> _P:
        page = self._context.new_page()
        response = page.goto(self.absolute(path))
        # `goto` returns None only for same-document navigations, never for a URL.
        assert response is not None
        return page_class(page, response.status, path, self._urls)
