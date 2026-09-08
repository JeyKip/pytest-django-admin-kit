"""The browser the admin is driven through.

One browser is launched per session and each test gets its own context, which is
what keeps cookies and storage from leaking between tests without paying to start a
browser every time.

Two details are borrowed from how Django drives its own browser tests. The browser is
launched with ``handle_sigint=False``, because the test runner has already installed a
handler and a second one swallows Ctrl-C. And the context's time zone is pinned, so a
rendered date does not depend on where the machine running the suite happens to be.
"""

from __future__ import annotations

from types import TracebackType

from playwright.sync_api import Browser, BrowserContext, Playwright, sync_playwright

from .config import Config


class BrowserLauncher:
    """Owns the driver process and the one browser shared by a session."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    @property
    def native(self) -> Browser:
        """Playwright's own ``Browser``, unwrapped.

        The package models what Django Admin renders. A project's custom widgets,
        overridden templates and third-party admin apps are driven through this
        handle, so it is public API, and a major version of Playwright is a major
        version of this package.
        """
        if self._browser is None:
            raise RuntimeError("The browser has not been started.")
        return self._browser

    def start(self) -> Browser:
        if self._browser is not None:
            return self._browser
        self._playwright = sync_playwright().start()
        try:
            browser_type = getattr(self._playwright, self._config.browser)
            self._browser = browser_type.launch(
                headless=self._config.headless,
                slow_mo=self._config.slow_mo,
                handle_sigint=False,
            )
        except BaseException:
            # The driver process is already running by this point. Leaving it up
            # would strand an event loop on this thread, and every later attempt to
            # start a browser would fail with an unrelated-looking error.
            self._playwright.stop()
            self._playwright = None
            raise
        return self._browser

    def new_context(self, base_url: str | None = None) -> BrowserContext:
        """Open an isolated context, timed out and time-zoned per the configuration."""
        # Both are Optional in the underlying API, so None means "unset" and there
        # is nothing to branch on.
        context = self.start().new_context(
            base_url=base_url,
            timezone_id=self._config.timezone,
        )
        context.set_default_timeout(self._config.timeout)
        return context

    def stop(self) -> None:
        """Close the browser, then the driver.

        This must run before ``live_server`` is torn down. A browser still holding a
        connection keeps the server thread from joining, and the run hangs with no
        failure to read. So the fixture that owns this launcher has to depend on
        ``live_server``, which is what makes pytest finalize it first.
        """
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    def __enter__(self) -> BrowserLauncher:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stop()
