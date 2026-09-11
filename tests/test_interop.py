"""Living alongside a project that drives Playwright itself.

Playwright's sync API allows one driver per thread, and two plugins each starting one
produce "using Playwright Sync API inside the asyncio loop" from whichever ran second.
This package no longer starts one at all: the browser comes from pytest-playwright, so
there is a single driver whichever fixture asks for it first, and the order tests run
in stopped being a variable.

What is still worth pinning is that the two sets of fixtures really do share that
browser, and that a session using both finishes instead of hanging.
"""

import os
import subprocess
import sys

import pytest


def test_the_admin_session_and_a_plain_page_share_one_browser(admin_ui, page):
    """One browser, so one driver. Separate contexts, so no shared cookies."""
    assert admin_ui.native.browser is page.context.browser
    assert admin_ui.native is not page.context


def test_a_plain_page_test_runs_in_the_same_session_as_admin_tests(page):
    """The collision this package used to cause. Nothing here needs the admin."""
    page.goto("about:blank")

    assert page.title() == ""


def test_the_admin_session_still_reaches_the_live_server(admin_ui, page, live_server):
    """Both fixtures in one test, driving the same server."""
    page.goto(live_server.url + "/admin/login/")
    admin_page = admin_ui.open(admin_ui.url.login()).native

    assert page.url == admin_page.url


def test_the_database_survives_the_browser_being_torn_down_mid_session(tmp_path):
    """The guard has to outlive the driver, not the browser.

    A guard that depends on `browser` dies with it while the driver is still up, and
    dropping the test database then raises SynchronousOnlyOperation. It only shows
    when the browser is torn down before the session ends, which a second `--browser`
    causes, so one browser is not enough to catch it.

    The child needs a clean environment. Once any admin test has run, this process has
    DJANGO_ALLOW_ASYNC_UNSAFE set, and a child inheriting it would restore that value
    instead of removing it, hiding the very fault this test looks for. Without the
    strip the result depends on what ran before it.

    It also needs its own --output. The child runs in the repository root so it can
    import the project, and pytest-playwright deletes the output directory at the
    start of every session, so a child sharing ours would wipe any artifacts this run
    had already written. Nothing is ever written to the child's, because it is not
    asked to record anything.
    """
    environment = {k: v for k, v in os.environ.items() if k != "DJANGO_ALLOW_ASYNC_UNSAFE"}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_session.py::test_a_superuser_reaches_the_index",
            "-q",
            "-p",
            "no:cacheprovider",
            "--browser",
            "chromium",
            "--browser",
            "firefox",
            "--output",
            str(tmp_path / "child-artifacts"),
        ],
        capture_output=True,
        text=True,
        timeout=300,
        env=environment,
    )

    if "Executable doesn't exist" in result.stdout:
        pytest.skip("firefox is not downloaded; run `playwright install firefox`")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "teardown test databases" not in result.stdout
