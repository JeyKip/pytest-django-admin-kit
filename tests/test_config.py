"""Settings resolution: defaults, precedence, and the errors a mistake produces."""

import warnings

import pytest
from django.core.exceptions import ImproperlyConfigured

from django_admin_kit.config import (
    BROWSERS,
    CommandLine,
    build_config,
    from_django_settings,
)


def test_the_defaults_need_no_settings_at_all():
    config = build_config()

    assert config.browser == "chromium"
    assert config.headless is True
    assert config.slow_mo == 0
    assert config.timeout == 30_000
    assert config.timezone is None


def test_settings_override_the_defaults():
    config = build_config(
        {"browser": "firefox", "headless": False, "slow_mo": 50, "timeout": 5_000}
    )

    assert config.browser == "firefox"
    assert config.headless is False
    assert config.slow_mo == 50
    assert config.timeout == 5_000


def test_the_command_line_overrides_settings():
    config = build_config(
        {"browser": "firefox", "slow_mo": 50, "headless": False},
        CommandLine(browser="webkit", slow_mo=10),
    )

    assert config.browser == "webkit"
    assert config.slow_mo == 10


def test_the_command_line_can_override_headless():
    """What `--admin-ui-headed` does: turn a headless setting into a visible run."""
    config = build_config({"headless": True}, CommandLine(headless=False))

    assert config.headless is False


def test_an_unset_headless_leaves_the_setting_alone():
    config = build_config({"headless": False}, CommandLine())

    assert config.headless is False


def test_the_timezone_falls_back_to_the_projects():
    config = build_config(default_timezone="Europe/Kyiv")

    assert config.timezone == "Europe/Kyiv"


def test_an_explicit_null_timezone_beats_the_projects():
    """None means "inherit the machine's zone", which is not the same as unset."""
    config = build_config({"timezone": None}, default_timezone="Europe/Kyiv")

    assert config.timezone is None


def test_an_unknown_setting_is_rejected_by_name():
    with pytest.raises(ImproperlyConfigured) as error:
        build_config({"headles": True})

    message = str(error.value)
    assert "'headles'" in message
    assert "'headless'" in message


def test_an_unsupported_browser_is_rejected_with_the_valid_list():
    with pytest.raises(ImproperlyConfigured) as error:
        build_config({"browser": "internet-explorer"})

    message = str(error.value)
    assert "'internet-explorer'" in message
    for browser in BROWSERS:
        assert repr(browser) in message


@pytest.mark.parametrize(
    ("settings", "expected"),
    [
        ({"timeout": 0}, "at least 1"),
        ({"timeout": "30000"}, "must be an integer"),
        ({"timeout": True}, "must be an integer"),
        ({"slow_mo": -1}, "at least 0"),
        ({"headless": "yes"}, "must be True or False"),
        ({"timezone": 3}, "must be an IANA zone name"),
    ],
)
def test_a_malformed_value_is_rejected(settings, expected):
    with pytest.raises(ImproperlyConfigured, match=expected):
        build_config(settings)


def test_slow_motion_without_a_visible_browser_warns():
    with pytest.warns(UserWarning, match="headless"):
        build_config({"slow_mo": 100})


def test_slow_motion_with_a_visible_browser_is_silent():
    with warnings.catch_warnings():
        warnings.simplefilter("error")

        build_config({"slow_mo": 100, "headless": False})


def test_django_settings_supply_the_project_time_zone():
    """A date must read the same in the browser as it does in a template."""
    config = from_django_settings()

    assert config.timezone == "UTC"
    assert config.browser == "chromium"


def test_django_settings_supply_the_settings_dict(settings):
    settings.DJANGO_ADMIN_KIT = {"browser": "firefox", "timeout": 1_000}

    config = from_django_settings()

    assert config.browser == "firefox"
    assert config.timeout == 1_000


def test_django_settings_are_still_validated(settings):
    settings.DJANGO_ADMIN_KIT = {"browsr": "firefox"}

    with pytest.raises(ImproperlyConfigured, match="browsr"):
        from_django_settings()


def test_a_site_must_be_a_dotted_path_not_an_instance():
    """Settings load before Django's app registry, so a project cannot import an
    AdminSite there. Saying so beats letting AppRegistryNotReady be the message."""
    from django.contrib.admin.sites import AdminSite

    with pytest.raises(ImproperlyConfigured, match="must be a dotted path"):
        build_config({"site": AdminSite(name="scratch")})


def test_a_site_path_is_carried_through_unresolved():
    """config holds the path; urls.resolve_site does the importing."""
    assert build_config({"site": "project.ops.ops_site"}).site == "project.ops.ops_site"
    assert build_config().site is None
