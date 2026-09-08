"""The pytest plugin: the command-line flags the package adds.

Registered through a ``pytest11`` entry point, so a project that installs the package
gets the flags without listing anything in its own configuration.
"""

from __future__ import annotations

import pytest

from .config import BROWSERS, CommandLine


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("django-admin-kit")
    group.addoption(
        "--admin-ui-browser",
        choices=BROWSERS,
        default=None,
        help="Browser to drive the admin with. Overrides the DJANGO_ADMIN_KIT setting.",
    )
    group.addoption(
        "--admin-ui-headed",
        action="store_true",
        default=False,
        help="Show the browser window instead of running it headless.",
    )
    group.addoption(
        "--admin-ui-slow-mo",
        type=int,
        default=None,
        metavar="MILLISECONDS",
        help="Pause before each browser operation so a headed run can be followed.",
    )


def command_line_options(config: pytest.Config) -> CommandLine:
    """The flags above, in the form the configuration layer resolves."""
    return CommandLine(
        browser=config.getoption("--admin-ui-browser"),
        headless=False if config.getoption("--admin-ui-headed") else None,
        slow_mo=config.getoption("--admin-ui-slow-mo"),
    )
