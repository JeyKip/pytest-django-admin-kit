"""The rows of a changelist and their cells, addressed by column name and by position.

The products are created in one order and the admin shows them in its own, by name,
so a test that reads the first row reads what the admin put there.
"""

import datetime
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import Locator

from django_admin_kit.matching import ANY, ANY_ROW
from django_admin_kit.rows import Link
from project.shop.models import Category, Product

# The Nut as the viewer's changelist shows it, one value per column.
NUT = ("Nut", "SKU-Nut", "10.00", True, None, "(none)", "False", "12.000", "Datasheet Manual")


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


def test_a_cell_that_links_to_the_change_page_reads_as_a_pair(admin_ui, viewer, products):
    admin_ui.login(viewer)

    cell = admin_ui.list(Product).rows[0]["name"]

    assert cell.value == "Bolt"
    assert cell.links == [("Bolt", admin_ui.url.edit(products[0]))]
    assert cell.links[0].text == "Bolt"
    assert cell.links[0].href.path == admin_ui.url.edit(products[0])


def test_a_cell_without_a_link_has_none(admin_ui, viewer, products):
    admin_ui.login(viewer)

    assert admin_ui.list(Product).rows[0]["sku"].links == []


def test_a_cell_may_carry_several_links(admin_ui, viewer, products):
    admin_ui.login(viewer)

    cell = admin_ui.list(Product).rows[0]["documents"]

    assert cell.value == "Datasheet Manual"
    assert cell.links == [
        ("Datasheet", "/media/SKU-Bolt/datasheet.pdf"),
        ("Manual", "/media/SKU-Bolt/manual.pdf"),
    ]
    assert cell.links == [
        ("Datasheet", urlsplit("/media/SKU-Bolt/datasheet.pdf")),
        Link("Manual", "/media/SKU-Bolt/manual.pdf"),
    ]


def test_a_link_keeps_what_the_admin_added_to_it(admin_ui, viewer, products):
    """With a filter applied the admin adds `_changelist_filters` to every change link
    so the filter survives a round trip. The href is read as rendered; the path is
    still the page."""
    admin_ui.login(viewer)
    page = admin_ui.list(Product)
    page.native.click("#changelist-filter a[href*='is_active__exact=1']")
    page.native.wait_for_load_state()

    link = page.rows[0]["name"].links[0]

    assert link != ("Bolt", admin_ui.url.edit(products[0]))
    assert link.href.path == admin_ui.url.edit(products[0])
    assert "_changelist_filters" in link.href.query


def test_a_row_knows_the_object_behind_it(admin_ui, viewer, products):
    admin_ui.login(viewer)

    rows = admin_ui.list(Product).rows

    assert [row.object for row in rows] == products


def test_a_row_without_a_change_link_has_no_object(admin_ui, superuser):
    """`CategoryAdmin` sets `list_display_links = None`, so nothing links anywhere."""
    Category.objects.create(name="Fasteners")
    admin_ui.login(superuser)

    row = admin_ui.list(Category).rows[0]

    assert row["name"].value == "Fasteners"
    assert row["name"].links == []
    assert row.object is None


def test_a_changelist_contains_a_row_given_as_literal_values(admin_ui, viewer, products):
    admin_ui.login(viewer)

    page = admin_ui.list(Product)

    assert page.contains(NUT)


def test_a_row_that_is_not_there_is_reported_with_the_rows_that_are(admin_ui, viewer, products):
    admin_ui.login(viewer)
    page = admin_ui.list(Product)
    screw = ("Screw", "SKU-Screw", *NUT[2:])

    with pytest.raises(AssertionError) as error:
        page.contains(screw)

    message = str(error.value)
    assert message.startswith(f"Expected row:\n    {screw!r}")
    assert "No matching row found." in message
    assert f"    {('Bolt', 'SKU-Bolt', *NUT[2:])!r}" in message
    assert message.count("\n    ('") == 4


def test_a_row_pattern_may_ask_for_the_links_a_cell_renders(admin_ui, viewer, products):
    admin_ui.login(viewer)

    page = admin_ui.list(Product)

    assert page.contains(
        (
            ("Bolt", admin_ui.url.edit(products[0])),
            "SKU-Bolt",
            *NUT[2:8],
            [
                ("Datasheet", "/media/SKU-Bolt/datasheet.pdf"),
                Link("Manual", "/media/SKU-Bolt/manual.pdf"),
            ],
        )
    )


def test_a_pattern_may_leave_cells_open_with_any(admin_ui, viewer, products):
    admin_ui.login(viewer)

    page = admin_ui.list(Product)

    assert page.contains(("Washer", "SKU-Washer", ANY, ANY, ANY, ANY, ANY, ANY, ANY))


def test_any_row_passes_when_there_is_a_row(admin_ui, viewer, product):
    admin_ui.login(viewer)

    assert admin_ui.list(Product).contains(ANY_ROW)


def test_any_row_fails_on_an_empty_changelist(admin_ui, superuser):
    admin_ui.login(superuser)

    with pytest.raises(AssertionError, match=r"Actual rows:\n    \(none\)"):
        admin_ui.list(Product).contains(ANY_ROW)


def test_a_callable_matches_a_cell_by_whatever_it_reads(admin_ui, viewer, products):
    admin_ui.login(viewer)

    page = admin_ui.list(Product)

    assert page.contains(("Bolt", lambda row, cell: cell.value.startswith("SKU-"), *NUT[2:]))
    assert page.contains(
        (
            lambda row, cell: cell.links[0].href.path == admin_ui.url.edit(products[1]),
            "SKU-Nut",
            *NUT[2:],
        )
    )


def test_a_row_may_be_described_by_a_few_named_columns(admin_ui, viewer, products):
    admin_ui.login(viewer)

    page = admin_ui.list(Product)

    assert page.contains({"name": "Nut", "is_active": True})
    assert page.contains({"name": ("Nut", admin_ui.url.edit(products[1])), "featured": None})


def test_a_named_column_that_is_not_there_raises(admin_ui, viewer, products):
    admin_ui.login(viewer)

    page = admin_ui.list(Product)

    with pytest.raises(KeyError, match=r"no column named 'colour'\. Columns: 'name'"):
        page.contains({"colour": "red"})
