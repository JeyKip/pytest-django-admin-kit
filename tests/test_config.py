"""Settings resolution: defaults, and the errors a mistake produces."""

import pytest
from django.core.exceptions import ImproperlyConfigured

from django_admin_kit.config import build_config, from_django_settings


def test_the_defaults_need_no_settings_at_all():
    config = build_config()

    assert config.site is None
    assert config.timeout == 30_000
    assert config.timezone is None
    assert config.locale is None


def test_settings_override_the_defaults():
    config = build_config({"timeout": 5_000, "timezone": "Europe/Kyiv", "locale": "uk"})

    assert config.timeout == 5_000
    assert config.timezone == "Europe/Kyiv"
    assert config.locale == "uk"


def test_the_timezone_and_locale_fall_back_to_the_projects():
    config = build_config(default_timezone="Europe/Kyiv", default_locale="uk")

    assert config.timezone == "Europe/Kyiv"
    assert config.locale == "uk"


def test_an_explicit_null_beats_the_projects():
    """None means "inherit the machine's", which is not the same as unset."""
    config = build_config(
        {"timezone": None, "locale": None}, default_timezone="Europe/Kyiv", default_locale="uk"
    )

    assert config.timezone is None
    assert config.locale is None


def test_an_unknown_setting_is_rejected_by_name():
    with pytest.raises(ImproperlyConfigured) as error:
        build_config({"timout": 1})

    message = str(error.value)
    assert "'timout'" in message
    assert "'timeout'" in message


@pytest.mark.parametrize(
    ("settings", "expected"),
    [
        ({"timeout": 0}, "at least 1"),
        ({"timeout": "30000"}, "must be an integer"),
        ({"timeout": True}, "must be an integer"),
        ({"timezone": 3}, "must be an IANA zone name"),
        ({"locale": 3}, "must be a language tag"),
    ],
)
def test_a_malformed_value_is_rejected(settings, expected):
    with pytest.raises(ImproperlyConfigured, match=expected):
        build_config(settings)


def test_django_settings_supply_the_project_time_zone_and_language():
    """A date must read the same in the browser as it does in a template."""
    config = from_django_settings()

    assert config.timezone == "UTC"
    assert config.locale == "en-us"


def test_django_settings_supply_the_settings_dict(settings):
    settings.DJANGO_ADMIN_KIT = {"timeout": 1_000}

    assert from_django_settings().timeout == 1_000


def test_django_settings_are_still_validated(settings):
    settings.DJANGO_ADMIN_KIT = {"browsr": "firefox"}

    with pytest.raises(ImproperlyConfigured, match="browsr"):
        from_django_settings()


def test_a_site_must_be_a_dotted_path_not_an_instance():
    from django.contrib.admin.sites import AdminSite

    with pytest.raises(ImproperlyConfigured, match="must be a dotted path"):
        build_config({"site": AdminSite(name="scratch")})


def test_a_site_path_is_carried_through_unresolved():
    assert build_config({"site": "project.ops.ops_site"}).site == "project.ops.ops_site"
