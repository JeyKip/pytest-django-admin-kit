"""Settings for the package, and the rules that reject a bad one loudly.

Values come from the ``DJANGO_ADMIN_KIT`` dict in Django settings, or a default. A
typo raises rather than being ignored, because a silently dropped key disables a
setting invisibly and the resulting test failure points nowhere near the cause.

Which browser to use, whether to show it, and how far to slow it down are not settings
here. They belong to the pytest plugin the package drives the browser through, and
duplicating its flags would give a project two places to say the same thing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from .normalize import DEFAULTS, Rule

SETTINGS_NAME = "DJANGO_ADMIN_KIT"

DEFAULT_TIMEOUT = 30_000

# Settings this package owns. Anything the browser plugin already governs is absent
# on purpose; see the module docstring.
_KNOWN_KEYS = frozenset({"locale", "normalizers", "site", "timeout", "timezone"})


@dataclass(frozen=True)
class Config:
    # A dotted path, resolved later by `urls.resolve_site`. It cannot be an
    # AdminSite instance: settings are imported before the app registry is ready, so
    # a project that wrote one here would fail with AppRegistryNotReady before this
    # package saw the value.
    site: str | None
    timeout: int
    timezone: str | None
    locale: str | None
    # The rules the project replaces, by kind, already imported. The kinds it leaves out
    # keep their defaults.
    normalizers: Mapping[str, Rule] = field(default_factory=dict)


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


def _rules(value: Any) -> dict[str, Rule]:
    """The project's rules by kind, each imported from its dotted path.

    A rule is named by its path, as the site is, so the settings module never imports
    project code before the app registry is ready.
    """
    key = f"{SETTINGS_NAME}['normalizers']"
    if not isinstance(value, Mapping):
        raise ImproperlyConfigured(
            f"{key} must be a dict of rule names to dotted paths, not {type(value).__name__}."
        )
    unknown = set(value) - set(DEFAULTS)
    if unknown:
        raise ImproperlyConfigured(
            f"Unknown {key} rule(s): {_quote(sorted(unknown))}. "
            f"Valid rules are: {_quote(DEFAULTS)}."
        )
    rules = {}
    for name, path in value.items():
        if not isinstance(path, str):
            raise ImproperlyConfigured(
                f"{key}[{name!r}] must be a dotted path to a callable, not {type(path).__name__}."
            )
        try:
            rule = import_string(path)
        except ImportError as error:
            raise ImproperlyConfigured(
                f"{key}[{name!r}] names {path!r}, which cannot be imported: {error}"
            ) from error
        if not callable(rule):
            raise ImproperlyConfigured(f"{key}[{name!r}] names {path!r}, which is not callable.")
        rules[name] = rule
    return rules


def build_config(
    settings: Mapping[str, Any] | None = None,
    default_timezone: str | None = None,
    default_locale: str | None = None,
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

    locale = given.get("locale", default_locale)
    if locale is not None and not isinstance(locale, str):
        raise ImproperlyConfigured(
            f"{SETTINGS_NAME}['locale'] must be a language tag such as 'en-us' or None, "
            f"not {type(locale).__name__}."
        )

    site = given.get("site")
    if site is not None and not isinstance(site, str):
        raise ImproperlyConfigured(
            f"{SETTINGS_NAME}['site'] must be a dotted path to an AdminSite, "
            f"not {type(site).__name__}."
        )

    normalizers = _rules(given.get("normalizers", {}))

    return Config(
        site=site, timeout=timeout, timezone=timezone, locale=locale, normalizers=normalizers
    )


def from_django_settings() -> Config:
    """Build the configuration from the project's own Django settings.

    The time zone defaults to the project's ``TIME_ZONE`` so that a rendered date
    reads the same in the browser as it does in a Django template. The locale
    defaults to ``LANGUAGE_CODE``, so a project whose admin follows the browser's
    ``Accept-Language`` renders the same language and formats on every machine.
    """
    return build_config(
        getattr(django_settings, SETTINGS_NAME, None),
        default_timezone=getattr(django_settings, "TIME_ZONE", None),
        default_locale=getattr(django_settings, "LANGUAGE_CODE", None),
    )
