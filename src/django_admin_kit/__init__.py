"""A pytest toolkit for writing conscious tests against the Django admin.

Public names are imported from the module that defines them, such as
``django_admin_kit.pages.AdminPage``. Nothing is re-exported here: this module runs
at pytest startup in every project that installs the package, and importing the
session, page or URL modules would load the admin and the browser for all of them.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pytest-django-admin-kit")
except PackageNotFoundError:  # pragma: no cover - running from a source tree
    __version__ = "0.0.0.dev0"

__all__ = ["__version__"]
