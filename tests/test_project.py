"""Smoke tests for the test project the package's own suite runs against.

These touch no package code and start no browser. They exist so that a failure in the
project setup — a missing app, a broken migration, a Django version that no longer
accepts these settings — is reported as itself rather than as a mysterious failure in
whatever feature is being worked on.
"""

from django.apps import apps
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.core.management import call_command
from django.urls import reverse


def test_the_project_passes_system_checks():
    """Two installed user models can clash on Group and Permission, and only Django's
    checks report it; the query that goes wrong depends on the Django version."""
    call_command("check")


def test_the_active_user_model_is_djangos_default():
    """The custom model is swapped in per test, never by the project."""
    assert get_user_model() is User


def test_the_custom_user_model_is_installed_but_not_registered():
    """Installed so its table exists; unregistered so the admin does not list two Users."""
    custom = apps.get_model("accounts", "User")

    assert custom.USERNAME_FIELD == "email"
    assert custom not in admin.site._registry


def test_the_admin_is_mounted_at_admin():
    assert reverse("admin:index") == "/admin/"


def test_the_admin_index_is_reachable(admin_client):
    assert admin_client.get(reverse("admin:index")).status_code == 200


def test_both_registered_models_have_a_changelist(admin_client):
    assert admin_client.get(reverse("admin:shop_product_changelist")).status_code == 200
    assert admin_client.get(reverse("admin:auth_user_changelist")).status_code == 200
