"""The rows of a changelist and their cells, addressed by column name and by position.

The products are created in one order and the admin shows them in its own, by name,
so a test that reads the first row reads what the admin put there.
"""

import datetime

import pytest
from playwright.sync_api import Locator

from project.shop.models import Product


def test_a_viewer_reads_a_cell_by_column_name(admin_ui, viewer, products):
    admin_ui.login(viewer)

    page = admin_ui.list(Product)

    assert page.rows[0]["name"].value == "Bolt"
    assert page.rows[0]["name"].text == "Bolt"
    assert page.rows[0]["sku"].value == "SKU-Bolt"
    assert page.rows[0]["price"].value == "10.00"


def test_a_cell_is_also_addressed_by_position(admin_ui, viewer, products):
    admin_ui.login(viewer)

    page = admin_ui.list(Product)

    assert page.rows[0][0].value == "Bolt"
    assert page.rows[0][1].value == "SKU-Bolt"
    assert page.rows[0][2].value == "10.00"


def test_rows_come_in_the_order_the_admin_shows_them(admin_ui, viewer, products):
    admin_ui.login(viewer)

    page = admin_ui.list(Product)

    assert len(page.rows) == 3
    assert [row["name"].value for row in page.rows] == ["Bolt", "Nut", "Washer"]
    assert [row.index for row in page.rows] == [0, 1, 2]


def test_a_superuser_reads_the_same_cells(admin_ui, superuser, products):
    """The superuser's rows carry the action checkbox and the viewer's do not.
    Neither has it as a cell."""
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert page.rows[0][0].value == "Bolt"
    assert page.rows[0]["name"].value == "Bolt"


def test_an_unknown_column_is_reported_with_the_ones_there(admin_ui, viewer, products):
    admin_ui.login(viewer)

    page = admin_ui.list(Product)

    with pytest.raises(KeyError, match=r"no column named 'colour'\. Columns: 'name', 'sku'"):
        page.rows[0]["colour"]


def test_an_empty_changelist_has_no_rows(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert page.works
    assert page.rows == []


def test_a_changelist_that_did_not_open_has_no_rows_to_read(admin_ui, adder):
    admin_ui.login(adder)

    page = admin_ui.list(Product)

    with pytest.raises(LookupError, match=r"did not open.*Status 403"):
        _ = page.rows


def test_a_row_and_a_cell_hand_out_their_elements(admin_ui, viewer, products):
    admin_ui.login(viewer)

    row = admin_ui.list(Product).rows[0]

    assert isinstance(row.native, Locator)
    assert isinstance(row["name"].native, Locator)
    assert row["name"].native.text_content().strip() == "Bolt"


def test_a_boolean_icon_reads_as_a_boolean(admin_ui, viewer, products):
    products[0].is_active = False
    products[0].save()
    admin_ui.login(viewer)

    page = admin_ui.list(Product)

    assert page.rows[0]["is_active"].value is False
    assert page.rows[1]["is_active"].value is True


def test_an_unknown_boolean_reads_as_none(admin_ui, viewer, products):
    admin_ui.login(viewer)

    cell = admin_ui.list(Product).rows[0]["featured"]

    assert cell.value is None
    assert cell.text == ""


def test_a_bool_the_admin_renders_as_text_reads_as_text(admin_ui, viewer, products):
    """Only a column that asks for the icon gets one; the rest show the word."""
    admin_ui.login(viewer)

    assert admin_ui.list(Product).rows[0]["is_released"].value == "False"


def test_an_empty_cell_reads_as_the_text_the_admin_shows_for_it(admin_ui, viewer, products):
    """`ProductAdmin` sets its own empty value, so the site's default never shows."""
    admin_ui.login(viewer)

    cell = admin_ui.list(Product).rows[0]["released_on"]

    assert cell.value == "(none)"
    assert cell.text == "(none)"


def test_a_date_reads_as_the_text_the_admin_renders(admin_ui, viewer, products):
    """The project's date format, not a date: the test sees what the user sees."""
    products[0].released_on = datetime.date(2026, 1, 15)
    products[0].save()
    admin_ui.login(viewer)

    row = admin_ui.list(Product).rows[0]

    assert row["released_on"].value == "Jan. 15, 2026"
    assert row["is_released"].value == "True"
