"""Fixtures shared by the suite: the users and products every page is tested with.

These are the test project's own. Nothing here reaches a project that installs the
package; the only fixtures it ships are the ones `django_admin_kit.plugin` registers.
Every user belongs to Django's default `auth.User`; `test_custom_user.py` overrides the
ones it needs against a model with no `username`.
"""

import datetime

import pytest
from django.contrib import admin
from django.contrib.auth.models import Permission, User

from django_admin_kit.urls import AdminUrls
from project.shop.models import Category, Product


def grant(user, *codenames):
    permissions = list(Permission.objects.filter(codename__in=codenames))
    assert len(permissions) == len(codenames), f"unknown permission among {codenames}"
    user.user_permissions.add(*permissions)


@pytest.fixture
def urls():
    return AdminUrls(admin.site)


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(username="alice", password="pw")


@pytest.fixture
def viewer(db):
    """May look at products and nothing else."""
    user = User.objects.create_user(username="vera", is_staff=True)
    grant(user, "view_product")
    return user


@pytest.fixture
def editor(db):
    """May look at and change products, but neither add nor delete one."""
    user = User.objects.create_user(username="eve", is_staff=True)
    grant(user, "view_product", "change_product")
    return user


@pytest.fixture
def adder(db):
    """May add products and nothing else, which lists the model on the index without a
    link and is not enough to open its changelist."""
    user = User.objects.create_user(username="adam", is_staff=True)
    grant(user, "add_product")
    return user


@pytest.fixture
def outsider(db):
    """Staff, so the admin opens, but with no permission on anything."""
    return User.objects.create_user(username="otto", is_staff=True)


@pytest.fixture
def customer(db):
    """Not staff, so the admin must refuse them."""
    return User.objects.create_user(username="carol", password="pw")


@pytest.fixture
def passwordless_staff(db):
    """The case a password-based login cannot serve: single sign-on users."""
    user = User.objects.create_user(username="bruno", is_staff=True)
    user.set_unusable_password()
    user.save()
    return user


@pytest.fixture
def category(db):
    return Category.objects.create(name="Tools")


@pytest.fixture
def product(db):
    return Product.objects.create(name="Widget", sku="SKU-1", price="10.00")


@pytest.fixture
def released(category):
    """A product with every field filled in, so each one has a value to read."""
    return Product.objects.create(
        name="Widget",
        sku="SKU-1",
        price="10.00",
        released_on=datetime.date(2026, 1, 15),
        category=category,
    )


@pytest.fixture
def products(db):
    return [
        Product.objects.create(name=name, sku=f"SKU-{name}", price="10.00")
        for name in ("Bolt", "Nut", "Washer")
    ]
