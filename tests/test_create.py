"""Whether the add page opens for each user."""

import pytest
from django.contrib.auth.models import Permission, User

from project.shop.models import Product


def grant(user, *codenames):
    permissions = list(Permission.objects.filter(codename__in=codenames))
    assert len(permissions) == len(codenames), f"unknown permission among {codenames}"
    user.user_permissions.add(*permissions)


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(username="alice", password="pw")


@pytest.fixture
def viewer(db):
    user = User.objects.create_user(username="vera", is_staff=True)
    grant(user, "view_product")
    return user


@pytest.fixture
def editor(db):
    user = User.objects.create_user(username="eve", is_staff=True)
    grant(user, "view_product", "change_product")
    return user


@pytest.fixture
def adder(db):
    user = User.objects.create_user(username="adam", is_staff=True)
    grant(user, "add_product")
    return user


@pytest.fixture
def customer(db):
    """Not staff, so the admin must refuse them."""
    return User.objects.create_user(username="carol", password="pw")


def test_a_superuser_reaches_the_add_page(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert page.works
    assert page.destination == admin_ui.url.create(Product)


def test_a_user_who_may_only_add_reaches_the_add_page(admin_ui, adder):
    admin_ui.login(adder)

    page = admin_ui.create(Product)

    assert page.works
    assert page.destination == admin_ui.url.create(Product)


def test_a_viewer_is_refused_in_place(admin_ui, viewer):
    admin_ui.login(viewer)

    page = admin_ui.create(Product)

    assert page.denied
    assert page.status_code == 403
    assert page.destination == admin_ui.url.create(Product)


def test_an_editor_is_refused_in_place(admin_ui, editor):
    """Changing products is one permission; adding one is another."""
    admin_ui.login(editor)

    page = admin_ui.create(Product)

    assert page.denied
    assert page.status_code == 403
    assert page.destination == admin_ui.url.create(Product)


def test_a_refused_user_is_sent_to_the_login_page(admin_ui, customer):
    admin_ui.login(customer)

    page = admin_ui.create(Product)

    assert page.denied
    assert page.status_code == 200
    assert page.destination == admin_ui.url.login()
