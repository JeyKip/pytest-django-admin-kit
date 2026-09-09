"""The plugin's fixtures, and what installing the package does to a session.

The browser flags belong to pytest-playwright, so there is nothing of ours to test
there. What is still ours is the promise that a project which never opens an admin
page is left exactly as it was.
"""

import os
import subprocess
import sys


def test_a_session_that_never_opens_the_admin_leaves_the_guard_alone(tmp_path):
    """Installing the package must not change how an existing test behaves.

    Runs in a subprocess. This session lifts the guard itself, so checking in process
    would only read our own state back. The child starts with the variable stripped
    from its environment, so if it reappears, the package put it there.
    """
    (tmp_path / "test_no_browser.py").write_text(
        "import os\n\n\ndef test_guard_intact():\n"
        "    assert 'DJANGO_ALLOW_ASYNC_UNSAFE' not in os.environ\n"
    )
    # DJANGO_SETTINGS_MODULE goes too: pytest-django exports it into the environment,
    # and the child runs from tmp_path where `project` is not importable.
    stripped = {"DJANGO_ALLOW_ASYNC_UNSAFE", "DJANGO_SETTINGS_MODULE"}
    environment = {k: v for k, v in os.environ.items() if k not in stripped}

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "test_no_browser.py", "-q", "-p", "no:cacheprovider"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=environment,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_the_plugin_pulls_no_admin_imports_into_startup():
    """`plugin` loads in every project that installs the package, so its fixtures
    import their dependencies lazily rather than dragging in django.contrib.admin."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import django_admin_kit.plugin; "
            "print([m for m in sys.modules if m.startswith('django.contrib')])",
        ],
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "[]", result.stdout + result.stderr


def test_the_admin_session_is_configured_from_the_layers_below(
    admin_ui, admin_ui_config, admin_ui_urls
):
    """The chain is overridable: a project can replace one fixture and keep the rest."""
    assert admin_ui.url is admin_ui_urls
    assert admin_ui_config.timezone == "UTC"


def test_the_guard_is_lifted_while_the_admin_session_is_live(admin_ui):
    """Logging in needs the ORM, and the ORM needs the guard off while a browser runs."""
    assert os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] == "true"
