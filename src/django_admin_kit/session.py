"""The object the ``admin_ui`` fixture yields.

Login builds the session in Django and hands the browser the resulting cookie. It
never types a password, because passwords are stored irreversibly and a test handed an
arbitrary user has no way to know one. A user created with ``set_unusable_password()``
has no password at all and must still be able to log in.
"""

from __future__ import annotations

from typing import Any, TypeVar, overload
from urllib.parse import urljoin

from django.conf import settings
from django.test import Client
from playwright.sync_api import BrowserContext

from .pages import (
    AdminPage,
    ChangelistPage,
    CreatePage,
    DeletePage,
    EditPage,
    IndexPage,
    LoginPage,
)
from .results import SubmissionResult
from .tools import PageTools
from .urls import AdminUrls

_P = TypeVar("_P", bound=AdminPage)


class AdminSession:
    """One test's view of the admin: who is logged in, and where things live."""

    def __init__(
        self,
        context: BrowserContext,
        tools: PageTools,
        base_url: str,
    ) -> None:
        self._context = context
        self._tools = tools
        self._base_url = base_url

    @property
    def native(self) -> BrowserContext:
        """The browsing context, unwrapped, for anything the package does not model."""
        return self._context

    @property
    def url(self) -> AdminUrls:
        """Admin URLs resolved through the site under test, as paths."""
        return self._tools.urls

    def absolute(self, path: str) -> str:
        """Turn an admin path into a full URL on the live server.

        The package navigates absolutely rather than setting the context's
        ``base_url``, which belongs to the project: a test suite already using
        ``--base-url`` for its own pages keeps it, and neither of us can break the
        other.
        """
        return urljoin(self._base_url, path)

    @overload
    def login(self) -> LoginPage: ...

    @overload
    def login(self, user: Any, password: None = None) -> None: ...

    @overload
    def login(self, user: Any, password: str) -> SubmissionResult: ...

    # For a password that may be None, such as one a test reads from its parameters.
    @overload
    def login(self, user: Any, password: str | None) -> SubmissionResult | None: ...

    def login(
        self, user: Any = None, password: str | None = None
    ) -> LoginPage | SubmissionResult | None:
        """Log in as ``user`` without knowing or needing a password.

        Calling it again replaces the session rather than adding a second one, so
        switching users mid-test works.

        With ``password``, the rendered login form is driven instead: the browser
        opens the login page, types what the user model identifies users by and the
        password, and submits. That is for tests whose subject is the login page, and
        the result says whether the admin let the user in. A wrong password leaves the
        browser on the form, with its error shown, and the session anonymous.

        Both log out first. With no arguments at all, nothing is logged out: the login
        page opens as the admin serves it to whoever is logged in now, to be filled and
        submitted by the test. The admin sends a staff user on to the index, and shows
        a user who isn't staff the form with a note saying so.
        """
        if user is None:
            if password is not None:
                raise TypeError("login() got a password but no user to type it for.")
            return self._open(self._tools.urls.login(), LoginPage)

        self.logout()

        if password is None:
            self._login_with_cookie(user)
            return None
        page = self.login()
        page.fill(username=user.get_username(), password=password)
        return page.submit()

    def _login_with_cookie(self, user: Any) -> None:
        client = Client()
        client.force_login(user)

        name = settings.SESSION_COOKIE_NAME
        self._context.add_cookies(
            [{"name": name, "value": client.cookies[name].value, "url": self._base_url}]
        )

    def logout(self) -> None:
        """Return the browser to anonymous by dropping its cookies."""
        self._context.clear_cookies()

    def open(self, path: str) -> AdminPage:
        """Open any admin path in a new page, including views the package does not
        model, and report how it went."""
        return self._open(path, AdminPage)

    def index(self) -> IndexPage:
        """Open the admin index."""
        return self._open(self._tools.urls.index(), IndexPage)

    def list(self, model: type[Any]) -> ChangelistPage:
        """Open a model's changelist."""
        return self._open(self._tools.urls.list(model), ChangelistPage, model)

    def create(self, model: type[Any]) -> CreatePage:
        """Open the page that adds a new instance of ``model``."""
        return self._open(self._tools.urls.create(model), CreatePage, model)

    def edit(self, instance: Any) -> EditPage:
        """Open the change page of ``instance``."""
        return self._open(self._tools.urls.edit(instance), EditPage, type(instance))

    def delete(self, instance: Any) -> DeletePage:
        """Open the page that asks whether to delete ``instance``."""
        return self._open(self._tools.urls.delete(instance), DeletePage, type(instance))

    def _open(self, path: str, page_class: type[_P], *args: Any) -> _P:
        page = self._context.new_page()
        response = page.goto(self.absolute(path))
        # `goto` returns None only for same-document navigations, never for a URL.
        assert response is not None
        return page_class(page, response.status, path, self._tools, *args)
