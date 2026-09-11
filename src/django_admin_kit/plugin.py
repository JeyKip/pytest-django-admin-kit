"""The pytest plugin: the fixtures the package adds.

Registered through a ``pytest11`` entry point, so a project that installs the package
gets them without listing anything in its own configuration. Every fixture is lazy and
none is autouse, so a project that installs the package and never uses ``admin_ui``
behaves exactly as it did before.

The browser comes from pytest-playwright, so its flags govern admin tests too:
``--browser``, ``--headed``, ``--slowmo`` and the rest mean here what they mean
everywhere else in the project. That also makes each admin test carry the browser it
ran on in its id.

The fixtures are layered so one can be overridden without rewriting the rest. Point
``admin_ui_urls`` at another ``AdminSite``, or ``admin_ui_config`` at different
settings, and ``admin_ui`` follows.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator, TypedDict

import pytest

from .config import Config, from_django_settings

# The real imports happen inside the fixtures. Doing them here would add roughly 400
# modules and 150ms to pytest startup in every project that installs the package,
# most of it django.contrib.admin. mypy reads this block; Python never runs it.
if TYPE_CHECKING:
    from pytest_django.live_server_helper import LiveServer
    from pytest_playwright.pytest_playwright import CreateContextCallback

    from .session import AdminSession
    from .urls import AdminUrls


_ASYNC_UNSAFE = "DJANGO_ALLOW_ASYNC_UNSAFE"


class _MachineIndependentContextArgs(TypedDict, total=False):
    """The context arguments the package sets so results do not depend on the machine."""

    timezone_id: str
    locale: str


@contextmanager
def _orm_allowed_while_driving() -> Iterator[None]:
    """Let the ORM run while a browser is live, and put the guard back afterwards.

    The driver's synchronous API leaves an asyncio event loop on the test thread, and
    Django then refuses every ORM call with ``SynchronousOnlyOperation``. Logging a
    user in needs the ORM, so the guard has to come off.
    """
    previous = os.environ.get(_ASYNC_UNSAFE)
    os.environ[_ASYNC_UNSAFE] = "true"
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(_ASYNC_UNSAFE, None)
        else:
            os.environ[_ASYNC_UNSAFE] = previous


@pytest.fixture(scope="session")
def admin_ui_config() -> Config:
    """Settings resolved once for the whole session."""
    return from_django_settings()


@pytest.fixture(scope="session")
def admin_ui_urls(admin_ui_config: Config) -> AdminUrls:
    """URLs for the configured admin site, resolved once."""
    # Imported here, not at module scope: this module loads at pytest startup in
    # every project that installs the package, and `urls` pulls in the whole of
    # django.contrib.admin.
    from .urls import AdminUrls, resolve_site

    return AdminUrls(resolve_site(admin_ui_config.site))


@pytest.fixture(scope="session")
def admin_ui_driving() -> Iterator[None]:
    """Hold Django's async guard open around everything the admin session touches.

    It depends on nothing, and in particular not on ``browser``. A guard that depends
    on the browser is torn down when the browser is, while the driver behind it is
    still running, and dropping the test database then fails with
    ``SynchronousOnlyOperation``. That surfaces only when the browser is torn down
    before the end of the session, which is what a second ``--browser`` does.

    Depending on nothing also lets ``admin_ui`` request it first, so it is set up
    before the database is built and torn down after the database is destroyed.

    Being a fixture rather than a session hook is what keeps it honest. A project that
    installs the package and never asks for ``admin_ui`` never runs this, and Django's
    guard stays where it was.
    """
    with _orm_allowed_while_driving():
        yield


@pytest.fixture
def admin_ui(
    # The guard comes first so it outlives the database at both ends. `live_server`
    # before `new_context` follows Django's own practice of closing the browser before
    # joining the live-server thread, since a held-open connection can deadlock it.
    # Inverting it here did not reproduce a hang, so treat that half as precaution
    # rather than a demonstrated fix.
    admin_ui_driving: None,
    live_server: LiveServer,
    new_context: CreateContextCallback,
    admin_ui_config: Config,
    admin_ui_urls: AdminUrls,
    browser_context_args: dict[str, Any],
) -> Iterator[AdminSession]:
    """A fresh, unauthenticated admin session per test.

    Each test gets its own browsing context, which is the isolation unit for cookies
    and storage. Sharing one would let a test that never calls ``login`` inherit the
    previous test's user, and whether it passed would depend on file order.

    The context comes from pytest-playwright's factory, so admin tests record video
    and traces on the same flags as every other browser test in the project.
    """
    from .session import AdminSession

    # Only pass what the project has not set itself: the factory merges its own
    # arguments with these, and a duplicate key raises TypeError. `base_url` is
    # deliberately absent, since AdminSession navigates absolutely.
    context_args: _MachineIndependentContextArgs = {}
    if admin_ui_config.timezone is not None and "timezone_id" not in browser_context_args:
        context_args["timezone_id"] = admin_ui_config.timezone
    if admin_ui_config.locale is not None and "locale" not in browser_context_args:
        context_args["locale"] = admin_ui_config.locale

    context = new_context(**context_args)
    context.set_default_timeout(admin_ui_config.timeout)

    # No close here: the factory closes the contexts it made when the test ends.
    yield AdminSession(context, admin_ui_urls, live_server.url)
