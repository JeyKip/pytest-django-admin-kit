"""Login, logout and user switching, driven through a real browser.

Every user here belongs to Django's default `auth.User`. A user model with no
`username` field is covered in `test_custom_user.py`.
"""

import pytest
from django.contrib.auth.models import User
from django.urls import reverse


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


def test_the_login_form_accepts_the_right_password(admin_ui, superuser):
    """The opt-in for tests whose subject is the login page."""
    admin_ui.login(superuser, password="pw")

    assert admin_ui.index().works


def test_the_login_form_refuses_the_wrong_password(admin_ui, superuser):
    admin_ui.login(superuser, password="wrong")

    form = admin_ui.native.pages[0]
    assert form.url.endswith(admin_ui.url.login())
    assert "Please enter the correct" in form.locator(".errornote").text_content()
    assert admin_ui.index().denied


def test_the_context_and_the_page_are_reachable_natively(admin_ui):
    """Anything the package does not model is driven through these handles."""
    page = admin_ui.index()

    assert page.native.context is admin_ui.native
    assert page.native.title()


def test_the_login_page_sends_a_logged_in_user_to_the_index(admin_ui, superuser):
    """Django's own behaviour, and not a missing page."""
    admin_ui.login(superuser)

    page = admin_ui.open(admin_ui.url.login())

    assert page.redirected
    assert not page.missing
    assert page.destination == admin_ui.url.index()


def test_any_admin_path_can_be_opened(admin_ui, superuser):
    """A view the package knows nothing about still gets an outcome and a handle."""
    admin_ui.login(superuser)

    page = admin_ui.open(reverse("admin:password_change"))

    assert page.works
    assert page.destination == "/admin/password_change/"
    assert page.native.title().startswith("Password change")


def test_a_path_the_admin_does_not_serve_is_missing(admin_ui, superuser):
    admin_ui.login(superuser)

    assert admin_ui.open("/admin/no/such/page/").missing


def test_absolute_builds_a_url_against_the_live_server(admin_ui, live_server):
    """For a test that needs a URL the package does not produce."""
    assert admin_ui.absolute("/admin/") == live_server.url + "/admin/"
