"""A second admin site, reached by overriding the `admin_ui_urls` fixture.

The project's default is `admin.site`. Each test here points the session at `ops_site`,
which registers only Product and is mounted at `/ops/`, so nothing in the package may
assume the default site or its prefix.
"""

import pytest
from django.contrib.auth.models import User

from django_admin_kit.urls import AdminUrls
from project.ops import ops_site

pytestmark = pytest.mark.urls("project.urls_with_ops")


@pytest.fixture
def admin_ui_urls():
    return AdminUrls(ops_site)


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(username="alice", password="pw")


@pytest.fixture
def customer(db):
    """Not staff, so the admin must refuse them."""
    return User.objects.create_user(username="carol", password="pw")


def test_a_superuser_reaches_the_index_of_the_site(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.index()

    assert page.works
    assert page.destination == "/ops/"
    assert "Site administration" in page.native.text_content("body")


def test_a_non_staff_user_is_sent_to_the_login_page_of_the_site(admin_ui, customer):
    admin_ui.login(customer)

    page = admin_ui.index()

    assert page.denied
    assert page.destination == "/ops/login/"
