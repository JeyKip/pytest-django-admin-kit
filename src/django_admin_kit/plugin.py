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

from typing import TYPE_CHECKING, Any, Iterator

import pytest

from .config import Config, from_django_settings

# The real imports happen inside the fixtures. Doing them here would add roughly 400
# modules and 150ms to pytest startup in every project that installs the package,
# most of it django.contrib.admin. mypy reads this block; Python never runs it.
if TYPE_CHECKING:
    from .session import AdminSession
    from .urls import AdminUrls


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

    It depends on nothing on purpose. Requested first by ``admin_ui``, it is set up
    before the test database is built and therefore torn down after the database is
    destroyed, so both ends are covered: creating tables while a driver is running
    raises ``SynchronousOnlyOperation``, and so does dropping them.

    Being a fixture rather than a session hook is what keeps it honest. A project that
    installs the package and never asks for ``admin_ui`` never runs this, and Django's
    guard stays where it was.
    """
    from .browser import orm_allowed_while_driving

    with orm_allowed_while_driving():
        yield


@pytest.fixture
def admin_ui(
    # The order of these three is load-bearing. The guard first, so it outlives the
    # database at both ends. Then `live_server`, so the browser that `new_context`
    # pulls in is set up after it and therefore torn down before it: a browser still
    # holding a connection open stops the server thread joining, and the run hangs
    # with no failure to read.
    admin_ui_driving: None,
    live_server: Any,
    new_context: Any,
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
    wanted = {"timezone_id": admin_ui_config.timezone}
    extra = {k: v for k, v in wanted.items() if v is not None and k not in browser_context_args}

    context = new_context(**extra)
    context.set_default_timeout(admin_ui_config.timeout)

    # No close here: the factory closes the contexts it made when the test ends.
    yield AdminSession(context, admin_ui_urls, live_server.url)
