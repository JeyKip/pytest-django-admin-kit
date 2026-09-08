"""The browser layer. These start real browsers, so they are the slow tests here."""

import pytest
from playwright.sync_api import Error as PlaywrightError

from django_admin_kit.browser import BrowserLauncher
from django_admin_kit.config import BROWSERS, build_config


def launcher(**settings):
    return BrowserLauncher(build_config(settings))


# The two ways a browser can be unavailable through no fault of this package: it was
# never downloaded, or the host lacks the shared libraries it links against. Matching
# on these exact phrases keeps a genuine launch failure from being skipped away.
_ENVIRONMENT_GAPS = {
    "Executable doesn't exist": "is not downloaded; run `playwright install {browser}`",
    "missing dependencies": (
        "needs host libraries this machine lacks; run `sudo playwright install-deps {browser}`"
    ),
}


@pytest.mark.parametrize("browser", BROWSERS)
def test_every_supported_browser_launches(browser):
    running = launcher(browser=browser)
    try:
        running.start()
    except PlaywrightError as error:
        for phrase, reason in _ENVIRONMENT_GAPS.items():
            if phrase in str(error):
                pytest.skip(f"{browser} {reason.format(browser=browser)}")
        raise

    try:
        assert running.native.is_connected()
        assert running.native.browser_type.name == browser
    finally:
        running.stop()


def test_the_context_carries_the_configured_timezone():
    with launcher(timezone="Australia/Sydney") as running:
        context = running.new_context()
        page = context.new_page()
        page.goto("about:blank")

        assert page.evaluate("Intl.DateTimeFormat().resolvedOptions().timeZone") == (
            "Australia/Sydney"
        )

        context.close()


def test_a_context_without_a_timezone_inherits_the_machines():
    with launcher() as running:
        context = running.new_context()
        page = context.new_page()
        page.goto("about:blank")

        assert page.evaluate("Intl.DateTimeFormat().resolvedOptions().timeZone")

        context.close()


def test_the_configured_timeout_bounds_an_operation():
    """A 1ms timeout cannot be met, so the operation must fail rather than hang."""
    with launcher(timeout=1) as running:
        context = running.new_context()
        page = context.new_page()

        with pytest.raises(PlaywrightError, match="Timeout 1ms"):
            page.goto("about:blank")
            page.wait_for_selector("#never-appears")

        context.close()


def test_contexts_do_not_share_storage():
    """Each test gets its own context, which is what keeps state from leaking."""
    with launcher() as running:
        first, second = running.new_context(), running.new_context()
        for context in (first, second):
            context.new_page().goto("about:blank")

        first.add_cookies([{"name": "session", "value": "first", "url": "https://example.test/"}])

        assert [cookie["value"] for cookie in first.cookies()] == ["first"]
        assert second.cookies() == []

        first.close()
        second.close()


def test_starting_twice_reuses_the_same_browser():
    with launcher() as running:
        assert running.start() is running.start()


def test_stopping_is_safe_to_repeat():
    running = launcher()
    running.start()
    running.stop()
    running.stop()

    with pytest.raises(RuntimeError, match=r"The browser has not been started\."):
        _ = running.native
