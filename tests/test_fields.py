"""Which fields the create and edit pages show, by name and in the admin's order."""

import pytest
from playwright.sync_api import Locator

from project.shop.models import Product

# The product form as the admin lays it out: the model's fields, then the rendered-only
# one the admin appends. The hidden `source` field is on the page but never shown.
FIELDS = [
    "name",
    "sku",
    "price",
    "is_active",
    "featured",
    "released_on",
    "category",
    "price_with_tax",
]


def test_the_add_page_lists_its_fields_in_the_admin_order(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert list(page.fields) == FIELDS


def test_fields_answer_membership_and_subset_checks(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert "name" in page.fields
    assert "colour" not in page.fields
    assert {"name", "price"} <= set(page.fields)


def test_a_field_knows_its_name(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert page.fields["name"].name == "name"
    assert repr(page.fields["name"]) == "FormField('name')"


def test_the_change_page_lists_the_product_fields(admin_ui, editor, product):
    admin_ui.login(editor)

    page = admin_ui.edit(product)

    assert list(page.fields) == FIELDS


def test_the_fields_are_listed_for_a_viewer_too(admin_ui, viewer, product):
    """The admin renders every field read-only for a viewer, and lists them all the same."""
    admin_ui.login(viewer)

    page = admin_ui.edit(product)

    assert list(page.fields) == FIELDS


def test_fields_sharing_a_line_are_listed_each_with_its_own_box(admin_ui, superuser):
    """The sku and the price are on one line; each field's box holds its own control and
    label, and nothing of the other's."""
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    for name in ("sku", "price"):
        native = page.fields[name].native
        assert isinstance(native, Locator)
        assert native.locator("input").count() == 1
        assert native.locator(f"input[name='{name}']").count() == 1
        assert native.locator("label").count() == 1


def test_a_hidden_field_is_on_the_page_but_not_among_the_fields(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert "source" not in page.fields
    assert page.native.locator("input[name='source']").count() == 1


def test_an_unknown_field_is_reported_with_the_ones_there(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    with pytest.raises(KeyError) as failure:
        page.fields["colour"]
    assert failure.value.args[0] == (
        "The form has no field named 'colour'. Fields: 'name', 'sku', 'price', 'is_active', "
        "'featured', 'released_on', 'category', 'price_with_tax'."
    )


def test_a_form_that_did_not_open_has_no_fields_to_read(admin_ui, viewer):
    """`"name" in page.fields` must not pass for a user who never saw the form."""
    admin_ui.login(viewer)

    page = admin_ui.create(Product)

    with pytest.raises(LookupError, match=r"did not open.*Status 403"):
        list(page.fields)


def test_the_native_handle_is_the_field_box_with_its_control_inside(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    native = page.fields["name"].native
    assert isinstance(native, Locator)
    assert native.locator("input[name='name']").count() == 1
    assert native.locator("label").count() == 1


def test_a_required_field_reads_as_required(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert page.fields["name"].required


def test_an_optional_field_reads_as_not_required(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert not page.fields["is_active"].required


def test_requiredness_is_the_forms_word_not_the_models(admin_ui, superuser):
    """The model lets the release date be blank; the admin's form requires it."""
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert Product._meta.get_field("released_on").blank
    assert page.fields["released_on"].required


def test_a_field_with_a_control_is_editable(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert page.fields["name"].editable


def test_a_field_rendered_only_is_not_editable(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert not page.fields["price_with_tax"].editable


def test_a_rendered_only_field_is_never_required(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert not page.fields["price_with_tax"].required


def test_the_required_fields_are_named_as_a_set(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert page.required_fields == {"name", "sku", "price", "released_on"}


def test_the_optional_fields_leave_out_what_cannot_be_filled(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert page.optional_fields == {"is_active", "featured", "category"}


def test_a_viewer_has_nothing_to_fill(admin_ui, viewer, product):
    """Every field is rendered only for a viewer, so none is required and none is optional."""
    admin_ui.login(viewer)

    page = admin_ui.edit(product)

    assert not page.fields["name"].editable
    assert not page.fields["name"].required
    assert page.required_fields == set()
    assert page.optional_fields == set()
