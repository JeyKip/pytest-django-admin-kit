"""Login and logout on a user model with no `username` field.

The project's default is `auth.User`. Each test here swaps in `accounts.User`, which
authenticates by email, so nothing in the package may assume a `username`.
"""

import pytest
from django.contrib.auth import get_user_model

from project.accounts.models import User


@pytest.fixture
def custom_user_model(settings):
    settings.AUTH_USER_MODEL = "accounts.User"


@pytest.fixture
def superuser(db, custom_user_model):
    return User.objects.create_superuser(email="root@example.com", password="pw")


@pytest.fixture
def passwordless_staff(db, custom_user_model):
    """Single sign-on users have no password at all."""
    user = User.objects.create_user(email="sso@example.com", is_staff=True)
    user.set_unusable_password()
    user.save()
    return user


def test_the_swapped_model_is_the_active_one(custom_user_model):
    assert get_user_model() is User
    assert "username" not in {field.name for field in User._meta.get_fields()}


def test_a_superuser_reaches_the_index(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.index()

    assert page.works
    assert "root@example.com" in page.native.text_content("body")


def test_a_user_with_no_usable_password_still_logs_in(admin_ui, passwordless_staff):
    assert not passwordless_staff.has_usable_password()

    admin_ui.login(passwordless_staff)

    assert admin_ui.index().works


def test_the_login_form_takes_the_email_as_the_identity(admin_ui, superuser):
    """The form's input is still called `username`; what goes in it is the email."""
    admin_ui.login(superuser, password="pw")

    assert admin_ui.index().works


def test_logout_returns_the_browser_to_anonymous(admin_ui, superuser):
    admin_ui.login(superuser)
    assert admin_ui.index().works

    admin_ui.logout()

    assert admin_ui.index().denied
