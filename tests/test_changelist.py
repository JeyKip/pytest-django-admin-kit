"""What a model's changelist reports to each user, read from the rendered page.

The count is what the page says, which is the total across all of its pages, not
the number of rows on the one that opened.
"""

import pytest

from project.shop.models import Product


def test_a_viewer_opens_the_changelist_and_reads_the_count(admin_ui, viewer, products):
    admin_ui.login(viewer)

    page = admin_ui.list(Product)

    assert page.works
    assert page.destination == admin_ui.url.list(Product)
    assert page.count == 3
    assert page.summary == "3 products"
    assert not page.empty


def test_one_record_is_reported_in_the_singular(admin_ui, superuser):
    Product.objects.create(name="Bolt", sku="SKU-1", price="10.00")
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert page.count == 1
    assert page.summary == "1 product"


def test_an_empty_changelist_says_so(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert page.works
    assert page.empty
    assert page.count == 0
    assert page.summary == "0 products"


def test_the_count_is_the_total_not_the_rows_on_one_page(admin_ui, superuser):
    """Past the admin's page size the paginator gains page links, which must not
    leak into either value."""
    Product.objects.bulk_create(
        Product(name=f"Product {n}", sku=f"SKU-{n}", price="10.00") for n in range(101)
    )
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert page.count == 101
    assert page.summary == "101 products"


def test_a_user_who_may_only_add_is_refused_in_place(admin_ui, adder):
    """The index lists the model for this user; the changelist still refuses them."""
    admin_ui.login(adder)

    page = admin_ui.list(Product)

    assert page.denied
    assert not page.works
    assert page.status_code == 403
    assert page.destination == admin_ui.url.list(Product)


def test_a_refused_user_is_sent_to_the_login_page(admin_ui, customer):
    admin_ui.login(customer)

    page = admin_ui.list(Product)

    assert page.denied
    assert page.destination == admin_ui.url.login()


def test_headers_are_the_labels_shown_in_order(admin_ui, superuser, products):
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert page.headers == ["Name", "Sku", "Price", "Is active", "Released on", "Price with tax"]
    assert page.columns == ["name", "sku", "price", "is_active", "released_on", "price_with_tax"]


def test_a_column_the_admin_computes_is_read_like_a_field(admin_ui, superuser, products):
    """It is no model field and cannot be sorted, so Django renders its label
    differently from the others. The reader does not care."""
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert page.has_header("Price with tax")
    assert page.has_column("price_with_tax")
    assert not page.has_header("price_with_tax")
    assert not page.has_column("Price with tax")


def test_a_user_without_actions_reads_the_same_columns(admin_ui, viewer, products):
    """The superuser's page has the action checkbox column and the viewer's does not.
    Neither is a column."""
    admin_ui.login(viewer)

    page = admin_ui.list(Product)

    assert page.headers == ["Name", "Sku", "Price", "Is active", "Released on", "Price with tax"]
    assert page.columns == ["name", "sku", "price", "is_active", "released_on", "price_with_tax"]


def test_an_empty_changelist_shows_no_columns(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert page.works
    assert page.headers == []
    assert page.columns == []
    assert not page.has_header("Name")
    assert not page.has_column("name")


def test_a_changelist_that_did_not_open_has_nothing_to_read(admin_ui, adder):
    """`assert page.empty` must not pass for a user who never saw the list."""
    admin_ui.login(adder)

    page = admin_ui.list(Product)

    for read in (
        lambda: page.count,
        lambda: page.summary,
        lambda: page.empty,
        lambda: page.headers,
        lambda: page.columns,
        lambda: page.has_header("Name"),
        lambda: page.has_column("name"),
        lambda: page.title,
        lambda: page.subtitle,
    ):
        with pytest.raises(LookupError, match=r"did not open.*Status 403"):
            read()


def test_a_changelist_names_its_model(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert page.title == "Select product to change"
    assert page.subtitle == ""


def test_a_viewer_is_told_the_changelist_is_read_only(admin_ui, viewer):
    """The title is how the admin tells the user what they may do here."""
    admin_ui.login(viewer)

    page = admin_ui.list(Product)

    assert page.title == "Select product to view"
    assert page.subtitle == ""
