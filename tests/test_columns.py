"""A changelist's columns as objects, and sorting by them."""

import pytest

from project.shop.models import Feed, Product

# The product columns the user can sort by: the fields, and the method with an ordering.
SORTABLE = ["name", "sku", "price", "is_active", "featured", "released_on", "is_released"]
# What a product column is called on the page, by the name it is addressed by.
LABELS = {"price": "Price", "is_released": "Released", "price_with_tax": "Price with tax"}
# The product columns, as the error of an unknown name lists them.
COLUMN_LIST = (
    "'name', 'sku', 'price', 'is_active', 'featured', 'released_on', 'is_released', "
    "'price_with_tax', 'documents'"
)


def test_the_sortable_columns_are_listed_in_the_order_shown(admin_ui, superuser, products):
    admin_ui.login(superuser)

    assert admin_ui.list(Product).sortable_columns == SORTABLE


def test_a_method_column_without_an_ordering_cannot_be_sorted(admin_ui, superuser, products):
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert page.has_column("price_with_tax")
    assert "price_with_tax" not in page.sortable_columns
    assert "documents" not in page.sortable_columns


def test_a_field_column_the_admin_leaves_out_of_sortable_by_cannot_be_sorted(
    admin_ui, superuser, feed
):
    """The feed's admin lets the user sort by the source and the two times only, and its two
    methods have no ordering."""
    admin_ui.login(superuser)

    page = admin_ui.list(Feed)

    assert page.has_column("mode")
    assert page.sortable_columns == ["source", "refreshed_at", "refresh_time"]


def test_a_user_without_actions_reads_the_same_sortable_columns(admin_ui, viewer, products):
    admin_ui.login(viewer)

    assert admin_ui.list(Product).sortable_columns == SORTABLE


def test_an_empty_changelist_has_no_sortable_columns(admin_ui, superuser):
    admin_ui.login(superuser)

    assert admin_ui.list(Product).sortable_columns == []


def test_a_page_that_did_not_open_cannot_list_its_sortable_columns(admin_ui, adder):
    admin_ui.login(adder)
    page = admin_ui.list(Product)

    with pytest.raises(LookupError, match="The page did not open"):
        _ = page.sortable_columns


@pytest.mark.parametrize("name", LABELS)
def test_a_column_reads_its_name_and_its_label(admin_ui, superuser, products, name):
    admin_ui.login(superuser)

    column = admin_ui.list(Product).column(name)

    assert column.name == name
    assert column.label == LABELS[name]


def test_a_column_reads_as_its_header_cell(admin_ui, superuser, products):
    admin_ui.login(superuser)

    column = admin_ui.list(Product).column("price")

    assert column.native.evaluate("cell => cell.tagName") == "TH"
    assert column.native.locator("div.text").text_content().strip() == "Price"


def test_a_column_shows_its_name_when_printed(admin_ui, superuser, products):
    admin_ui.login(superuser)

    assert repr(admin_ui.list(Product).column("price")) == "ChangelistColumn('price')"


def test_a_column_says_whether_it_can_be_sorted_as_the_page_lists_it(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    sortable = {name: page.column(name).sortable for name in page.columns}

    assert sortable == {name: name in SORTABLE for name in page.columns}


def test_a_user_without_actions_reads_the_same_column(admin_ui, viewer, products):
    admin_ui.login(viewer)

    column = admin_ui.list(Product).column("price")

    assert column.label == "Price"
    assert column.sortable is True


@pytest.mark.parametrize("name", ["color", "-price", "Price"])
def test_a_name_the_page_does_not_show_raises_listing_the_columns(
    admin_ui, superuser, products, name
):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    with pytest.raises(LookupError) as raised:
        page.column(name)

    assert str(raised.value) == f"No column named {name!r} here. Columns: {COLUMN_LIST}."


def test_an_empty_changelist_has_no_column_to_return(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    with pytest.raises(LookupError) as raised:
        page.column("price")

    assert str(raised.value) == "No column named 'price' here. The changelist shows no columns."


def test_a_page_that_did_not_open_has_no_column_to_return(admin_ui, adder):
    admin_ui.login(adder)
    page = admin_ui.list(Product)

    with pytest.raises(LookupError, match="The page did not open"):
        page.column("price")


def test_a_column_the_page_no_longer_shows_raises(admin_ui, superuser, products):
    """A search that finds nothing leaves the changelist without a table."""
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    column = page.column("price")

    page.search("nothing like it")

    with pytest.raises(LookupError, match="The page no longer shows the column 'price'"):
        _ = column.label


def test_a_column_keeps_working_after_the_page_loads_again(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    column = page.column("price")

    page.search("Bolt")

    assert column.label == "Price"
    assert column.sortable is True
