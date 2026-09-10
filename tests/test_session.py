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


def visit(admin_ui, path):
    page = admin_ui.native.new_page()
    page.goto(admin_ui.absolute(path))
    return page


def test_a_superuser_reaches_the_index(admin_ui, superuser):
    admin_ui.login(superuser)

    page = visit(admin_ui, admin_ui.url.index())

    assert page.url.endswith("/admin/")
    assert "Site administration" in page.text_content("body")


def test_a_user_with_no_usable_password_still_logs_in(admin_ui, passwordless_staff):
    """The whole reason login injects a cookie instead of typing into the form."""
    assert not passwordless_staff.has_usable_password()

    admin_ui.login(passwordless_staff)
    page = visit(admin_ui, admin_ui.url.index())

    assert page.url.endswith("/admin/")


def test_a_non_staff_user_is_sent_to_the_login_page(admin_ui, customer):
    admin_ui.login(customer)

    page = visit(admin_ui, admin_ui.url.index())

    assert "/login/" in page.url


def test_each_test_starts_anonymous(admin_ui):
    """No login here at all. A session leaked from another test would show up as
    reaching the index instead of the login page."""
    page = visit(admin_ui, admin_ui.url.index())

    assert "/login/" in page.url


def test_switching_users_changes_who_the_admin_reports(admin_ui, superuser, passwordless_staff):
    admin_ui.login(superuser)
    first = visit(admin_ui, admin_ui.url.index()).text_content("body")

    admin_ui.login(passwordless_staff)
    second = visit(admin_ui, admin_ui.url.index()).text_content("body")

    assert "alice" in first
    assert "bruno" in second
    assert "alice" not in second


def test_logout_returns_the_browser_to_anonymous(admin_ui, superuser):
    admin_ui.login(superuser)
    assert visit(admin_ui, admin_ui.url.index()).url.endswith("/admin/")

    admin_ui.logout()

    assert "/login/" in visit(admin_ui, admin_ui.url.index()).url


def test_the_context_is_reachable_natively(admin_ui):
    """Anything the package does not model is driven through this handle."""
    page = admin_ui.native.new_page()
    page.goto(admin_ui.absolute(admin_ui.url.login()))

    assert page.title()
