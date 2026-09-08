"""Settings for the package, and the rules that reject a bad one loudly.

Values come from three places, in order of precedence: a pytest command-line flag,
the ``DJANGO_ADMIN_KIT`` dict in Django settings, then the default. A typo in that
dict raises rather than being ignored, because a silently dropped key disables a
setting invisibly and the resulting test failure points nowhere near the cause.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured

SETTINGS_NAME = "DJANGO_ADMIN_KIT"

# The browsers the underlying library supports. The first is the default.
BROWSERS = ("chromium", "firefox", "webkit")

DEFAULT_TIMEOUT = 30_000
DEFAULT_SLOW_MO = 0

_KNOWN_KEYS = frozenset({"browser", "headless", "slow_mo", "timeout", "timezone"})


@dataclass(frozen=True)
class CommandLine:
    """What the command line asked for. ``None`` means it asked for nothing.

    These are intents, not the flags themselves: ``--admin-ui-headed`` is a
    store-true flag, so the plugin translates its absence to ``None`` rather than
    passing ``False`` through and losing the difference between "run headed" and
    "no opinion".
    """

    browser: str | None = None
    headless: bool | None = None
    slow_mo: int | None = None


@dataclass(frozen=True)
class Config:
    browser: str
    headless: bool
    slow_mo: int
    timeout: int
    timezone: str | None


def _quote(values: Iterable[str]) -> str:
    return ", ".join(repr(value) for value in values)


def _positive_int(value: Any, key: str, minimum: int) -> int:
    # bool is a subclass of int, so without the first check `"timeout": True` would
    # pass as a 1ms timeout and every browser operation would fail for no visible
    # reason.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ImproperlyConfigured(
            f"{SETTINGS_NAME}['{key}'] must be an integer, not {type(value).__name__}."
        )
    if value < minimum:
        raise ImproperlyConfigured(f"{SETTINGS_NAME}['{key}'] must be at least {minimum}.")
    return value


def build_config(
    settings: Mapping[str, Any] | None = None,
    command_line: CommandLine | None = None,
    default_timezone: str | None = None,
) -> Config:
    """Resolve the settings dict and the command line into one frozen Config."""
    given = dict(settings or {})
    command_line = command_line or CommandLine()

    unknown = set(given) - _KNOWN_KEYS
    if unknown:
        raise ImproperlyConfigured(
            f"Unknown {SETTINGS_NAME} setting(s): {_quote(sorted(unknown))}. "
            f"Valid settings are: {_quote(sorted(_KNOWN_KEYS))}."
        )

    browser = command_line.browser or given.get("browser", BROWSERS[0])
    if browser not in BROWSERS:
        raise ImproperlyConfigured(
            f"{SETTINGS_NAME}['browser'] is {browser!r}, which is not a supported browser. "
            f"Valid browsers are: {_quote(BROWSERS)}."
        )

    headless = given.get("headless", True)
    if not isinstance(headless, bool):
        raise ImproperlyConfigured(
            f"{SETTINGS_NAME}['headless'] must be True or False, not {type(headless).__name__}."
        )
    if command_line.headless is not None:
        headless = command_line.headless

    slow_mo = command_line.slow_mo
    if slow_mo is None:
        slow_mo = given.get("slow_mo", DEFAULT_SLOW_MO)
    slow_mo = _positive_int(slow_mo, "slow_mo", minimum=0)

    timeout = _positive_int(given.get("timeout", DEFAULT_TIMEOUT), "timeout", minimum=1)

    timezone = given.get("timezone", default_timezone)
    if timezone is not None and not isinstance(timezone, str):
        raise ImproperlyConfigured(
            f"{SETTINGS_NAME}['timezone'] must be an IANA zone name or None, "
            f"not {type(timezone).__name__}."
        )

    if slow_mo > 0 and headless:
        # slow_mo exists so a headed run can be watched. Headless, it only makes the
        # suite slower.
        warnings.warn(
            f"{SETTINGS_NAME}['slow_mo'] is {slow_mo}ms but the browser is headless, "
            "so there is nothing to watch. Pass --admin-ui-headed to see the run.",
            stacklevel=2,
        )

    return Config(
        browser=browser,
        headless=headless,
        slow_mo=slow_mo,
        timeout=timeout,
        timezone=timezone,
    )


def from_django_settings(command_line: CommandLine | None = None) -> Config:
    """Build the configuration from the project's own Django settings.

    The time zone defaults to the project's ``TIME_ZONE`` so that a rendered date
    reads the same in the browser as it does in a Django template.
    """
    return build_config(
        getattr(django_settings, SETTINGS_NAME, None),
        command_line,
        default_timezone=getattr(django_settings, "TIME_ZONE", None),
    )
