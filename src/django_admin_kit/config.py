"""Settings for the package, and the rules that reject a bad one loudly.

Values come from the ``DJANGO_ADMIN_KIT`` dict in Django settings, or a default. A
typo raises rather than being ignored, because a silently dropped key disables a
setting invisibly and the resulting test failure points nowhere near the cause.

Which browser to use, whether to show it, and how far to slow it down are not settings
here. They belong to the pytest plugin the package drives the browser through, and
duplicating its flags would give a project two places to say the same thing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured

SETTINGS_NAME = "DJANGO_ADMIN_KIT"

DEFAULT_TIMEOUT = 30_000

# Settings this package owns. Anything the browser plugin already governs is absent
# on purpose; see the module docstring.
_KNOWN_KEYS = frozenset({"site", "timeout", "timezone"})


@dataclass(frozen=True)
class Config:
    # A dotted path, resolved later by `urls.resolve_site`. It cannot be an
    # AdminSite instance: settings are imported before the app registry is ready, so
    # a project that wrote one here would fail with AppRegistryNotReady before this
    # package saw the value.
    site: str | None
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
    default_timezone: str | None = None,
) -> Config:
    """Resolve the settings dict into one frozen Config."""
    given = dict(settings or {})

    unknown = set(given) - _KNOWN_KEYS
    if unknown:
        raise ImproperlyConfigured(
            f"Unknown {SETTINGS_NAME} setting(s): {_quote(sorted(unknown))}. "
            f"Valid settings are: {_quote(sorted(_KNOWN_KEYS))}."
        )

    timeout = _positive_int(given.get("timeout", DEFAULT_TIMEOUT), "timeout", minimum=1)

    timezone = given.get("timezone", default_timezone)
    if timezone is not None and not isinstance(timezone, str):
        raise ImproperlyConfigured(
            f"{SETTINGS_NAME}['timezone'] must be an IANA zone name or None, "
            f"not {type(timezone).__name__}."
        )

    site = given.get("site")
    if site is not None and not isinstance(site, str):
        raise ImproperlyConfigured(
            f"{SETTINGS_NAME}['site'] must be a dotted path to an AdminSite, "
            f"not {type(site).__name__}."
        )

    return Config(site=site, timeout=timeout, timezone=timezone)


def from_django_settings() -> Config:
    """Build the configuration from the project's own Django settings.

    The time zone defaults to the project's ``TIME_ZONE`` so that a rendered date
    reads the same in the browser as it does in a Django template.
    """
    return build_config(
        getattr(django_settings, SETTINGS_NAME, None),
        default_timezone=getattr(django_settings, "TIME_ZONE", None),
    )
