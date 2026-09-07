import importlib.metadata

import django_admin_kit


def test_package_exposes_a_version():
    assert isinstance(django_admin_kit.__version__, str)
    assert django_admin_kit.__version__


def test_version_comes_from_the_distribution_metadata():
    """`pyproject.toml` is the single source of truth; `__version__` must not hardcode one."""
    declared = importlib.metadata.version("pytest-django-admin-kit")

    assert django_admin_kit.__version__ == declared
