"""A pytest toolkit for writing conscious tests against the Django admin."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pytest-django-admin-kit")
except PackageNotFoundError:  # pragma: no cover - running from a source tree
    __version__ = "0.0.0.dev0"

__all__ = ["__version__"]
