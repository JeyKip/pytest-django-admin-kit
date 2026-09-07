"""Smoke tests for the test project the package's own suite runs against.

These touch no package code and start no browser. They exist so that a failure in the
project setup — a missing app, a broken migration, a Django version that no longer
accepts these settings — is reported as itself rather than as a mysterious failure in
whatever feature is being worked on.
"""

from django.apps import apps
from django.contrib.auth import get_user_model
from django.urls import reverse


def test_the_active_user_model_is_the_projects_own():
    """The package must never assume `auth.User`."""
    user_model = get_user_model()

    assert user_model is apps.get_model("accounts", "User")
    assert user_model.USERNAME_FIELD == "email"


def test_the_user_model_has_no_username_field():
    """A `username` field is the assumption most likely to be baked in by accident."""
    field_names = {field.name for field in get_user_model()._meta.get_fields()}

    assert "username" not in field_names


def test_the_admin_is_not_mounted_at_admin():
    """The admin prefix must be resolved, never assumed."""
    assert reverse("admin:index") == "/backoffice/"


def test_the_admin_index_is_reachable(admin_client):
    assert admin_client.get(reverse("admin:index")).status_code == 200


def test_both_registered_models_have_a_changelist(admin_client):
    assert admin_client.get(reverse("admin:shop_product_changelist")).status_code == 200
    assert admin_client.get(reverse("admin:accounts_user_changelist")).status_code == 200
