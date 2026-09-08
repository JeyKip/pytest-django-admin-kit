"""The two things the browser plugin leaves to us.

The browser, its flags and its lifecycle all come from pytest-playwright. What that
plugin does not do is make a browser and Django's ORM coexist, and that is what this
module holds.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

ASYNC_UNSAFE = "DJANGO_ALLOW_ASYNC_UNSAFE"


@contextmanager
def orm_allowed_while_driving() -> Iterator[None]:
    """Let the ORM run while a browser is live, and put the guard back afterwards.

    The driver's synchronous API leaves an asyncio event loop on the test thread, and
    Django then refuses every ORM call with ``SynchronousOnlyOperation``. Logging a
    user in needs the ORM, so the guard has to come off.

    It comes off for as long as a browser is running and no longer. A project that
    installs this package but never opens an admin page keeps Django's guard intact.
    """
    previous = os.environ.get(ASYNC_UNSAFE)
    os.environ[ASYNC_UNSAFE] = "true"
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(ASYNC_UNSAFE, None)
        else:
            os.environ[ASYNC_UNSAFE] = previous


@dataclass(frozen=True)
class SessionCookie:
    """The session cookie to hand the browser, built Django-side.

    Only the name and value. Django's other ``SESSION_COOKIE_*`` settings are
    deliberately not copied: a project's production ``SESSION_COOKIE_DOMAIN`` will not
    match the live server's localhost, and ``SESSION_COOKIE_SECURE`` stops the browser
    sending the cookie back over the live server's plain http. Copying either would
    turn a working login into a silent anonymous session.
    """

    name: str
    value: str

    def as_playwright(self, url: str) -> dict[str, Any]:
        """The cookie in the browser's own format, scoped by URL rather than domain."""
        return {"name": self.name, "value": self.value, "url": url}
