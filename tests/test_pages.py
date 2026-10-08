"""The access-outcome resolver, fed each way the admin answers a page request.

Only the login redirect can be produced through the index page, so the other answers
are fed to the resolver directly. The browser tests in `test_session.py` cover the
redirect end to end.
"""

import pytest

from django_admin_kit.pages import AdminPage


class FakePage:
    def __init__(self, url):
        self.url = url


@pytest.fixture
def page_at(urls, admin_ui_normalizers):
    """Builds a page that answered ``status`` at ``path``, having been asked for
    ``requested``, or for ``path`` itself."""

    def build(path, status, requested=None):
        native = FakePage("http://localhost:8000" + path)
        return AdminPage(native, status, requested or path, urls, admin_ui_normalizers)

    return build


def outcome(page):
    return {name for name in ("works", "denied", "missing", "redirected") if getattr(page, name)}


def test_a_page_that_loads_where_it_was_asked_works(page_at, urls):
    page = page_at("/admin/", 200)

    assert outcome(page) == {"works"}
    assert page.destination == urls.index()


def test_a_redirect_to_the_login_page_is_denied_whatever_it_carries(page_at, urls):
    """The URL is the only sign: the login page itself answers 200."""
    page = page_at("/admin/login/?next=/admin/", 200, requested="/admin/")

    assert outcome(page) == {"denied", "redirected"}
    assert page.destination == urls.login()


def test_a_refusal_in_place_is_denied_though_the_url_did_not_change(page_at):
    """Staff without permission for a model: same URL, 403."""
    page = page_at("/admin/shop/product/", 403)

    assert outcome(page) == {"denied"}
    assert page.destination == "/admin/shop/product/"


def test_an_object_that_does_not_exist_is_missing_not_denied(page_at):
    """The admin sends a permitted user to the index with a message."""
    page = page_at("/admin/", 200, requested="/admin/shop/product/999/change/")

    assert outcome(page) == {"missing", "redirected"}


def test_the_login_page_sending_a_logged_in_user_to_the_index_is_only_a_redirect(page_at):
    page = page_at("/admin/", 200, requested="/admin/login/")

    assert outcome(page) == {"redirected"}


def test_a_url_the_admin_does_not_serve_is_missing(page_at):
    page = page_at("/admin/shop/nothing/", 404)

    assert outcome(page) == {"missing"}


def test_a_server_error_is_none_of_the_outcomes(page_at):
    page = page_at("/admin/", 500)

    assert outcome(page) == set()
    assert page.status_code == 500


def test_the_status_and_the_page_are_exposed(urls, admin_ui_normalizers):
    native = FakePage("http://localhost:8000/admin/")
    page = AdminPage(native, 200, "/admin/", urls, admin_ui_normalizers)

    assert page.status_code == 200
    assert page.native is native
