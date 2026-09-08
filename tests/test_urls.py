import pytest
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured

from django_admin_kit.urls import AdminUrls, resolve_site
from project.accounts.models import User
from project.ops import ops_site
from project.shop.models import Product


@pytest.fixture
def urls():
    return AdminUrls(admin.site)


@pytest.fixture
def product():
    return Product(pk=7, name="Widget", sku="W-1", price="9.99")


def test_urls_carry_the_projects_own_prefix(urls):
    """The admin here is at /backoffice/, so nothing may hardcode /admin/."""
    assert urls.index() == "/backoffice/"
    assert urls.login() == "/backoffice/login/"
    assert urls.list(Product) == "/backoffice/shop/product/"
    assert urls.create(Product) == "/backoffice/shop/product/add/"


def test_instance_urls_carry_the_primary_key(urls, product):
    assert urls.edit(product) == f"/backoffice/shop/product/{product.pk}/change/"
    assert urls.delete(product) == f"/backoffice/shop/product/{product.pk}/delete/"


@pytest.mark.urls("project.urls_with_ops")
def test_a_second_site_resolves_to_its_own_prefix():
    """Both sites share the `admin` app namespace, so the site's name is what picks."""
    default = AdminUrls(admin.site)
    ops = AdminUrls(ops_site)

    assert default.index() == "/backoffice/"
    assert ops.index() == "/ops/"
    assert ops.list(Product) == "/ops/shop/product/"


@pytest.mark.urls("project.urls_with_ops")
def test_a_site_only_knows_the_models_it_registers():
    """The default site has User; the ops site does not. Same model, different answer."""
    assert AdminUrls(admin.site).list(User) == "/backoffice/accounts/user/"

    with pytest.raises(LookupError, match=r"accounts\.User is not registered"):
        AdminUrls(ops_site).list(User)


def test_an_unregistered_model_is_reported_not_guessed(urls):
    with pytest.raises(LookupError) as error:
        urls.list(ContentType)

    message = str(error.value)
    assert "contenttypes.ContentType is not registered" in message
    assert "shop.Product" in message  # what it does know, so the mistake is obvious


def test_an_unsaved_instance_has_no_url(urls):
    with pytest.raises(ValueError, match=r"unsaved shop\.Product"):
        urls.edit(Product(name="Draft", sku="D-1", price="1.00"))


def test_resolution_does_not_depend_on_access(urls, product):
    """A URL exists whether or not anyone may open it. Access is a separate question."""
    assert urls.delete(product).endswith("/delete/")


def test_the_default_site_is_used_when_none_is_configured():
    assert resolve_site() is admin.site


def test_a_site_can_be_given_as_a_dotted_path():
    assert resolve_site("project.ops.ops_site") is ops_site


def test_a_dotted_path_that_does_not_import_is_reported():
    with pytest.raises(ImproperlyConfigured, match="does not import"):
        resolve_site("project.ops.no_such_site")


def test_a_path_to_something_other_than_a_site_is_reported():
    with pytest.raises(ImproperlyConfigured, match="not an AdminSite"):
        resolve_site("project.shop.models.Product")
