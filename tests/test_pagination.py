"""Reading the pages of a changelist from the paginator the admin draws."""

import pytest

from project.shop.admin import ProductAdmin
from project.shop.models import Product


@pytest.fixture
def per_page(monkeypatch):
    """Sets how many products the changelist shows on a page, for one test."""
    return lambda count: monkeypatch.setattr(ProductAdmin, "list_per_page", count)


@pytest.fixture
def many_products(db):
    """Creates ``count`` products, named so the changelist lists them in the order created."""
    return lambda count: [
        Product.objects.create(name=f"Product {number:02}", sku=f"SKU-{number}", price="1.00")
        for number in range(1, count + 1)
    ]


def at_page(page, number):
    """Takes the browser to page ``number`` of the changelist, as its link would."""
    page.native.goto(f"{page.native.url.split('?')[0]}?p={number}")


def test_a_changelist_on_one_page_is_page_1_of_1(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    assert page.page_number == 1
    assert page.page_count == 1


def test_an_empty_changelist_is_page_1_of_1(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    assert page.empty
    assert page.page_number == 1
    assert page.page_count == 1


def test_a_changelist_opens_on_its_first_page(admin_ui, superuser, per_page, many_products):
    per_page(2)
    many_products(5)
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert page.page_number == 1
    assert page.page_count == 3


@pytest.mark.parametrize("number", [2, 3])
def test_the_page_shown_is_the_one_the_paginator_marks(
    admin_ui, superuser, per_page, many_products, number
):
    """The last page has no link of its own, so its number is read from the mark alone."""
    per_page(2)
    many_products(5)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    at_page(page, number)

    assert page.page_number == number
    assert page.page_count == 3


@pytest.mark.parametrize("number", [1, 10, 20])
def test_the_count_includes_the_pages_the_paginator_leaves_out(
    admin_ui, superuser, per_page, many_products, number
):
    """Django shows the first two pages, the last two and three on each side of the current
    one, with an ellipsis for the rest."""
    per_page(1)
    many_products(20)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    at_page(page, number)

    assert "…" in page.native.locator(".paginator").inner_text()
    assert page.page_number == number
    assert page.page_count == 20


def test_the_rows_are_those_of_the_page_shown(admin_ui, superuser, per_page, many_products):
    per_page(2)
    many_products(5)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    at_page(page, 3)

    assert page.count == 5
    assert [row["name"].value for row in page.rows] == ["Product 05"]


def test_a_page_that_did_not_open_has_no_pages_to_read(admin_ui, adder):
    admin_ui.login(adder)
    page = admin_ui.list(Product)

    with pytest.raises(LookupError, match="The page did not open"):
        _ = page.page_number
    with pytest.raises(LookupError, match="The page did not open"):
        _ = page.page_count
