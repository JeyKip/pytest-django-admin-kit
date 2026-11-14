"""A changelist's columns as objects, and sorting by them."""

import pytest

from project.shop.models import Feed, Product

# The product columns the user can sort by: the fields, and the method with an ordering.
SORTABLE = ["name", "sku", "price", "is_active", "featured", "released_on", "is_released"]


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
