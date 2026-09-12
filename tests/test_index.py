"""What the admin index lists for each user, read from the rendered page.

The default site registers Product from the test project and User and Group from
`django.contrib.auth`, which gives two apps and one app with two models.
"""

import pytest
from django.contrib.auth.models import Group, Permission, User

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
def adder(db):
    """May add products and nothing else, so the index lists Product without a link."""
    user = User.objects.create_user(username="adam", is_staff=True)
    grant(user, "add_product")
    return user


@pytest.fixture
def outsider(db):
    """Staff, so the index opens, but with no permission on anything."""
    return User.objects.create_user(username="otto", is_staff=True)


@pytest.fixture
def customer(db):
    """Not staff, so the admin must refuse them."""
    return User.objects.create_user(username="carol", password="pw")


def test_a_superuser_sees_every_app_and_model_in_the_admins_order(admin_ui, superuser):
    """Apps alphabetically by name, models by verbose name within an app."""
    admin_ui.login(superuser)

    page = admin_ui.index()

    assert page.apps == ["Authentication and Authorization", "Shop"]
    assert page.models == [Group, User, Product]


def test_a_user_sees_only_the_apps_and_models_they_have_a_permission_on(admin_ui, viewer):
    admin_ui.login(viewer)

    page = admin_ui.index()

    assert page.apps == ["Shop"]
    assert page.models == [Product]


def test_a_model_the_user_may_only_add_is_still_listed(admin_ui, adder):
    """The admin lists it without a changelist link, so links are not what is read."""
    admin_ui.login(adder)

    page = admin_ui.index()

    assert page.apps == ["Shop"]
    assert page.models == [Product]


def test_a_model_the_user_may_not_see_is_not_listed(admin_ui, outsider):
    admin_ui.login(outsider)

    page = admin_ui.index()

    assert page.works
    assert page.apps == []
    assert page.models == []


def test_a_refused_user_sees_nothing(admin_ui, customer):
    """They landed on the login page, which lists no models; `denied` says why."""
    admin_ui.login(customer)

    page = admin_ui.index()

    assert page.denied
    assert page.apps == []
    assert page.models == []
