"""Login, logout and user switching, driven through a real browser.

Every user here belongs to Django's default `auth.User`. A user model with no
`username` field is covered in `test_custom_user.py`.
"""

import pytest
from django.urls import reverse

from django_admin_kit.pages import LoginPage

# The note the admin puts on the login page for a logged-in user who is not staff.
NOT_STAFF_NOTE = (
    "You are authenticated as carol, but are not authorized to access this page. "
    "Would you like to login to a different account?"
)


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
    result = admin_ui.login(superuser, password="pw")

    assert result.success
    assert result.redirected_to_index()
    assert admin_ui.index().works


def test_the_login_form_refuses_the_wrong_password(admin_ui, superuser):
    result = admin_ui.login(superuser, password="wrong")

    assert not result.success
    assert result.page.destination == admin_ui.url.login()
    assert "Please enter the correct" in result.page.native.locator(".errornote").text_content()
    assert admin_ui.index().denied


def test_a_refused_login_carries_the_login_page(admin_ui, superuser):
    result = admin_ui.login(superuser, password="wrong")

    assert isinstance(result.page, LoginPage)
    assert result.page.works


def test_an_empty_password_is_not_sent_by_the_browser(admin_ui, superuser):
    """The input is required, so the browser keeps the form; nothing waits for a page."""
    result = admin_ui.login(superuser, password="")

    assert not result.success
    assert result.page.destination == admin_ui.url.login()
    assert admin_ui.index().denied


def test_a_password_of_spaces_is_typed_as_given_and_refused(admin_ui, superuser):
    result = admin_ui.login(superuser, password="   ")

    assert not result.success
    assert admin_ui.index().denied


def test_a_password_without_a_user_is_refused(admin_ui):
    with pytest.raises(TypeError, match="no user"):
        admin_ui.login(password="pw")


def test_login_with_no_arguments_opens_the_blank_form(admin_ui):
    page = admin_ui.login()

    assert isinstance(page, LoginPage)
    assert page.works
    assert page.destination == admin_ui.url.login()
    assert page.native.locator('input[name="username"]').input_value() == ""


def test_opening_the_login_page_as_staff_leads_to_the_index_and_keeps_the_session(
    admin_ui, superuser
):
    """The admin's own answer to a staff user asking for the login page."""
    admin_ui.login(superuser)

    page = admin_ui.login()

    assert page.redirected
    assert page.destination == admin_ui.url.index()
    assert admin_ui.index().works


def test_opening_the_login_page_as_a_user_who_is_not_staff_keeps_the_session(admin_ui, customer):
    """The admin shows the form with a note naming who is logged in."""
    admin_ui.login(customer)

    page = admin_ui.login()

    assert page.works
    note = page.native.locator("#content-main .errornote").text_content()
    assert " ".join(note.split()) == NOT_STAFF_NOTE


def test_the_opened_form_logs_in_once_filled_and_submitted(admin_ui, superuser):
    page = admin_ui.login()
    page.fill(username="alice", password="pw")

    result = page.submit()

    assert result.success
    assert result.redirected_to_index()
    assert admin_ui.index().works


def test_a_user_who_is_not_staff_logs_in_as_someone_else_from_the_form(
    admin_ui, customer, superuser
):
    admin_ui.login(customer)
    page = admin_ui.login()
    page.fill(username="alice", password="pw")

    assert page.submit().success
    # The admin welcomes the user it has logged in by name, in bold.
    assert admin_ui.index().native.text_content("#user-tools strong") == "alice"


def test_a_refused_form_is_the_same_page_and_is_filled_again(admin_ui, superuser):
    """The admin renders the username back, so only the password is typed again."""
    page = admin_ui.login()
    page.fill(username="alice", password="wrong")
    refused = page.submit()

    refused.page.fill(password="pw")
    result = refused.page.submit()

    assert refused.page is page
    assert result.success


def test_filling_one_input_leaves_the_other_as_it_is(admin_ui):
    page = admin_ui.login()

    page.fill(username="alice")
    page.fill(password="pw")

    assert page.native.locator('input[name="username"]').input_value() == "alice"
    assert page.native.locator('input[name="password"]').input_value() == "pw"


def test_a_form_the_browser_keeps_is_no_success_on_the_same_page(admin_ui, superuser):
    page = admin_ui.login()
    page.fill(username="alice")

    result = page.submit()

    assert not result.success
    assert result.page is page
    assert page.works


def test_a_login_page_the_browser_left_fails_at_once(admin_ui, left_for, superuser):
    page = admin_ui.login()
    page.fill(username="alice", password="pw")
    page.submit()

    with pytest.raises(LookupError) as failure:
        page.fill(password="pw")

    assert str(failure.value) == left_for(admin_ui.url.index())


def test_the_context_and_the_page_are_reachable_natively(admin_ui):
    """Anything the package does not model is driven through these handles."""
    page = admin_ui.index()

    assert page.native.context is admin_ui.native
    assert page.native.title()


def test_the_login_page_sends_a_logged_in_user_to_the_index(admin_ui, superuser):
    """Django's own behavior, and not a missing page."""
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


def test_an_arbitrary_page_has_an_identity(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.open(reverse("admin:password_change"))

    assert page.title == "Password change"
    assert page.subtitle == ""


def test_a_page_the_admin_gives_no_title_reads_as_empty(admin_ui):
    """The login page sets a title for the window but renders none on the page."""
    page = admin_ui.open(admin_ui.url.login())

    assert page.works
    assert page.title == ""
    assert page.subtitle == ""


def test_a_path_the_admin_does_not_serve_is_missing(admin_ui, superuser):
    admin_ui.login(superuser)

    assert admin_ui.open("/admin/no/such/page/").missing


def test_absolute_builds_a_url_against_the_live_server(admin_ui, live_server):
    """For a test that needs a URL the package does not produce."""
    assert admin_ui.absolute("/admin/") == live_server.url + "/admin/"
