"""Every read goes to the page as it is now, and to the database as it is now.

A script changes the page in place here, as the admin's own scripts and a project's
widgets do, so the suite proves that nothing read before the change is read again.
"""

from project.shop.models import Product


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
