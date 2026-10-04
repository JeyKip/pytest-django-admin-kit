"""Every read goes to the page as it is now, and to the database as it is now.

A script changes the page in place here, as the admin's own scripts and a project's
widgets do, so the suite proves that nothing read before the change is read again.
"""

import pytest

from project.shop.models import Product

# The index as the admin marks it, served at the changelist's own URL: the same address,
# another kind of page.
INDEX_MARKUP = "<html><body class='dashboard'><div id='content'><h1>Site</h1></div></body></html>"

# Every way of reading a changelist, and the row and cell taken from it, by what it reads.
CHANGELIST_READERS = {
    "rows": lambda page, row, cell: page.rows,
    "count": lambda page, row, cell: page.count,
    "headers": lambda page, row, cell: page.headers,
    "held row": lambda page, row, cell: len(row),
    "held row's object": lambda page, row, cell: row.object,
    "held cell": lambda page, row, cell: cell.value,
}


def test_a_cell_changed_in_place_reads_its_new_text(admin_ui, viewer, products):
    admin_ui.login(viewer)
    page = admin_ui.list(Product)
    cell = page.rows[0]["sku"]
    assert cell.value == "SKU-Bolt"

    page.native.evaluate(
        "document.querySelector('#result_list tbody tr .field-sku').textContent = 'SKU-M8'"
    )

    assert cell.value == "SKU-M8"


def test_a_held_row_reads_the_record_now_at_its_position(admin_ui, viewer, products):
    """A row is a position, the way a locator's `nth` is, so the Nut moving up into the
    first place is what the first row reads."""
    admin_ui.login(viewer)
    page = admin_ui.list(Product)
    row = page.rows[0]
    assert row["name"].value == "Bolt"

    page.native.evaluate("document.querySelector('#result_list tbody tr').remove()")

    assert row["name"].value == "Nut"


def test_the_fields_read_again_leave_out_one_a_script_removed(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Product)
    before = page.fields

    page.native.evaluate("document.querySelector('.form-row.field-quantity').remove()")

    assert "quantity" not in page.fields
    assert "quantity" in before


def test_the_object_behind_a_row_is_read_as_it_is_stored_now(admin_ui, viewer, products):
    admin_ui.login(viewer)
    page = admin_ui.list(Product)
    row = page.rows[0]
    assert row.object.name == "Bolt"

    Product.objects.filter(name="Bolt").update(name="Bolt M8")

    assert row.object.name == "Bolt M8"


@pytest.mark.parametrize("read", CHANGELIST_READERS.values(), ids=CHANGELIST_READERS.keys())
def test_a_changelist_the_browser_left_fails_at_once_when_read(
    admin_ui, left_for, viewer, products, read
):
    admin_ui.login(viewer)
    page = admin_ui.list(Product)
    row = page.rows[0]
    cell = row["name"]

    page.native.goto(admin_ui.absolute(admin_ui.url.index()))

    with pytest.raises(LookupError) as failure:
        read(page, row, cell)

    assert str(failure.value) == left_for(admin_ui.url.index())


def test_another_kind_of_page_at_the_same_address_fails_at_once(
    admin_ui, left_for, viewer, products
):
    admin_ui.login(viewer)
    page = admin_ui.list(Product)
    page.native.route(
        admin_ui.absolute(admin_ui.url.list(Product)),
        lambda route: route.fulfill(status=200, content_type="text/html", body=INDEX_MARKUP),
    )

    page.native.reload()

    with pytest.raises(LookupError) as failure:
        int(page.count)

    assert str(failure.value) == left_for(admin_ui.url.list(Product))
