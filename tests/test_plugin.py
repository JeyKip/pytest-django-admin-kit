"""The pytest plugin: that its flags are really registered, and that installing the
package changes nothing else about a session."""

import os

from django_admin_kit.config import build_config
from django_admin_kit.plugin import command_line_options


def test_the_flags_are_registered_with_pytest(pytestconfig):
    """Registered through the entry point, not by anything this suite does."""
    assert pytestconfig.getoption("--admin-ui-browser") is None
    assert pytestconfig.getoption("--admin-ui-headed") is False
    assert pytestconfig.getoption("--admin-ui-slow-mo") is None


def test_the_flags_read_back_as_a_command_line(pytestconfig):
    options = command_line_options(pytestconfig)

    assert options.browser is None
    assert options.headless is None
    assert options.slow_mo is None


def test_unset_flags_leave_the_settings_in_charge(pytestconfig):
    config = build_config({"browser": "firefox"}, command_line_options(pytestconfig))

    assert config.browser == "firefox"


def test_installing_the_package_leaves_the_environment_alone():
    """A project that installs the package but never drives a browser must be
    unaffected. Lifting Django's async guard session-wide would not be."""
    assert "DJANGO_ALLOW_ASYNC_UNSAFE" not in os.environ
