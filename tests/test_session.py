"""Login, logout and user switching, driven through a real browser.

Every user here belongs to Django's default `auth.User`. A user model with no
`username` field is covered in `test_custom_user.py`.
"""

import pytest
from django.contrib.auth.models import User


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(username="alice", password="pw")


@pytest.fixture
def passwordless_staff(db):
    """The case a password-based login cannot serve: single sign-on users."""
    user = User.objects.create_user(username="bruno", is_staff=True)
    user.set_unusable_password()
    user.save()
    return user


@pytest.fixture
def customer(db):
    """Not staff, so the admin must refuse them."""
    return User.objects.create_user(username="carol", password="pw")


def test_a_superuser_reaches_the_index(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.index()

    assert page.works
    assert page.status_code == 200
    assert page.destination == admin_ui.url.index()


def test_a_user_with_no_usable_password_still_logs_in(admin_ui, passwordless_staff):
    """The whole reason login injects a cookie instead of typing into the form."""
    assert not passwordless_staff.has_usable_password()

    admin_ui.login(passwordless_staff)

    assert admin_ui.index().works


def test_a_non_staff_user_is_sent_to_the_login_page(admin_ui, customer):
    admin_ui.login(customer)

    page = admin_ui.index()

    assert page.denied
    assert not page.works
    assert page.destination == admin_ui.url.login()


def test_each_test_starts_anonymous(admin_ui):
    """No login here at all. A session leaked from another test would show up as
    reaching the index instead of the login page."""
    page = admin_ui.index()

    assert page.denied
    assert page.destination == admin_ui.url.login()


def test_switching_users_changes_who_the_admin_reports(admin_ui, superuser, passwordless_staff):
    admin_ui.login(superuser)
    first = admin_ui.index().native.text_content("body")

    admin_ui.login(passwordless_staff)
    second = admin_ui.index().native.text_content("body")

    assert "alice" in first
    assert "bruno" in second
    assert "alice" not in second


def test_logout_returns_the_browser_to_anonymous(admin_ui, superuser):
    admin_ui.login(superuser)
    assert admin_ui.index().works

    admin_ui.logout()

    assert admin_ui.index().denied


def test_the_context_and_the_page_are_reachable_natively(admin_ui):
    """Anything the package does not model is driven through these handles."""
    page = admin_ui.index()

    assert page.native.context is admin_ui.native
    assert page.native.title()
