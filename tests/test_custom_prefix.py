"""The admin mounted somewhere other than `/admin/`.

The project's default is `/admin/`. Each test here swaps in a URLconf that serves the
admin at `/backoffice/`, so nothing in the package may hardcode the prefix.
"""

import pytest
from django.contrib.auth.models import User

pytestmark = pytest.mark.urls("project.urls_backoffice")


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(username="alice", password="pw")


def test_urls_follow_the_prefix(admin_ui):
    assert admin_ui.url.index() == "/backoffice/"
    assert admin_ui.url.login() == "/backoffice/login/"


def test_a_superuser_reaches_the_index_under_the_prefix(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.native.new_page()
    page.goto(admin_ui.absolute(admin_ui.url.index()))

    assert page.url.endswith("/backoffice/")
    assert "Site administration" in page.text_content("body")
