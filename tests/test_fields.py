"""Which fields the create and edit pages show, by name and in the admin's order, and
what each one says about itself."""

import datetime

import django
import pytest
from django.utils import translation
from playwright.sync_api import Locator

from django_admin_kit.fields import FieldChoice
from project.shop.models import Product

# The product form as the admin lays it out: the model's fields, then the rendered-only
# one the admin appends. The hidden `source` field is on the page but never shown.
FIELDS = [
    "name",
    "sku",
    "price",
    "quantity",
    "is_active",
    "featured",
    "released_on",
    "category",
    "price_with_tax",
]

# The option a select shows for no choice. Django 6.1 reworded it; the package reports
# what the admin renders, so the suite proves the reader on both wordings.
BLANK = ("", "- Select an option -" if django.VERSION >= (6, 1) else "---------")


@pytest.fixture
def released(category):
    """A product with every field filled in, so each one has a value to read."""
    return Product.objects.create(
        name="Widget",
        sku="SKU-1",
        price="10.00",
        released_on=datetime.date(2026, 1, 15),
        category=category,
    )


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
        "The form has no field named 'colour'. Fields: 'name', 'sku', 'price', 'quantity', "
        "'is_active', 'featured', 'released_on', 'category', 'price_with_tax'."
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

    assert page.required_fields == {"name", "sku", "price", "quantity", "released_on"}


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


def test_a_text_control_reads_as_its_text(admin_ui, editor, released):
    admin_ui.login(editor)

    page = admin_ui.edit(released)

    assert page.fields["name"].value == "Widget"


def test_a_number_control_reads_as_its_text(admin_ui, editor, released):
    admin_ui.login(editor)

    page = admin_ui.edit(released)

    assert page.fields["price"].value == "10.00"


def test_a_date_control_reads_as_the_text_typed_in_it(admin_ui, editor, released):
    admin_ui.login(editor)

    page = admin_ui.edit(released)

    assert page.fields["released_on"].value == "2026-01-15"


def test_a_checkbox_reads_as_a_boolean(admin_ui, editor, released):
    admin_ui.login(editor)

    page = admin_ui.edit(released)

    assert page.fields["is_active"].value is True


def test_a_select_reads_as_the_choice_made(admin_ui, editor, released, category):
    admin_ui.login(editor)

    page = admin_ui.edit(released)

    value = page.fields["category"].value
    assert value == FieldChoice(str(category.pk), "Tools")
    assert value == (str(category.pk), "Tools")
    assert value.value == str(category.pk)
    assert value.label == "Tools"


def test_a_select_with_nothing_chosen_reads_as_the_blank_choice(admin_ui, editor, product):
    admin_ui.login(editor)

    page = admin_ui.edit(product)

    assert page.fields["category"].value == BLANK


def test_a_nullable_boolean_is_a_select_and_reads_as_its_choice(admin_ui, editor, released):
    admin_ui.login(editor)

    page = admin_ui.edit(released)

    assert page.fields["featured"].value == ("unknown", "Unknown")


def test_a_rendered_only_field_reads_as_its_text(admin_ui, editor, released):
    admin_ui.login(editor)

    page = admin_ui.edit(released)

    assert page.fields["price_with_tax"].value == "12.000"


def test_a_viewer_reads_text_fields_as_the_admin_renders_them(admin_ui, viewer, released):
    """A viewer gets every field rendered only: a number and a date in the display
    format rather than the input format, and a category as the name it links to."""
    admin_ui.login(viewer)

    page = admin_ui.edit(released)

    assert page.fields["name"].value == "Widget"
    assert page.fields["sku"].value == "SKU-1"
    assert page.fields["price"].value == "10.00"
    assert page.fields["quantity"].value == "1"
    assert page.fields["released_on"].value == "Jan. 15, 2026"
    assert page.fields["category"].value == "Tools"
    assert page.fields["price_with_tax"].value == "12.000"


def test_a_viewer_reads_a_boolean_icon_as_a_boolean(admin_ui, viewer, released):
    admin_ui.login(viewer)

    page = admin_ui.edit(released)

    assert page.fields["is_active"].value is True
    assert page.fields["featured"].value is None


def test_a_viewer_reads_an_unset_category_as_the_empty_value(admin_ui, viewer, product):
    admin_ui.login(viewer)

    page = admin_ui.edit(product)

    assert page.fields["category"].value == "(none)"


def test_the_add_page_starts_with_the_initial_values(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert page.fields["name"].value == ""
    assert page.fields["sku"].value == ""
    assert page.fields["price"].value == ""
    assert page.fields["quantity"].value == "1"
    assert page.fields["is_active"].value is True
    assert page.fields["featured"].value == ("unknown", "Unknown")
    assert page.fields["released_on"].value == ""
    assert page.fields["category"].value == BLANK
    assert page.fields["price_with_tax"].value == "(none)"


def test_a_label_is_read_without_the_suffix_after_it(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert page.fields["released_on"].label == "Released on"


def test_a_checkbox_label_has_no_suffix_to_take_off(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert page.fields["is_active"].label == "Is active"


def test_a_rendered_only_field_has_a_label_too(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert page.fields["price_with_tax"].label == "Price with tax"


def test_a_viewer_reads_the_same_labels(admin_ui, viewer, product):
    admin_ui.login(viewer)

    page = admin_ui.edit(product)

    assert page.fields["name"].label == "Name"
    assert page.fields["is_active"].label == "Is active"


@pytest.mark.parametrize(
    ("language", "shown"),
    [
        ("en", "Name:"),
        ("fr", "Name\xa0:"),  # a non-breaking space before the colon
        ("zh-hant", "Name\uff1a"),  # a full-width colon
    ],
)
def test_the_suffix_is_the_one_of_the_language_the_page_was_rendered_in(
    admin_ui, superuser, settings, language, shown
):
    """The test project's own labels are not translated, so only the suffix changes
    with the language, and whatever it is, it is taken off."""
    settings.LANGUAGE_CODE = language
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert page.fields["name"].native.locator("label").text_content() == shown
    assert page.fields["name"].label == "Name"


def test_the_suffix_follows_the_page_not_the_test_process(admin_ui, superuser):
    """The page is rendered in the project's language whatever the test thread has
    activated; the label is read with the page's suffix, not the thread's. Traditional
    Chinese is the one locale whose suffix is not a colon at all."""
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    with translation.override("zh-hant"):
        assert page.fields["name"].native.locator("label").text_content() == "Name:"
        assert page.fields["name"].label == "Name"


def test_a_select_offers_its_choices_in_order_with_the_blank_one(admin_ui, superuser, category):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert page.fields["category"].choices == [BLANK, (str(category.pk), "Tools")]


def test_a_nullable_boolean_offers_its_three_choices(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert page.fields["featured"].choices == [
        ("unknown", "Unknown"),
        ("true", "Yes"),
        ("false", "No"),
    ]


def test_a_choice_is_looked_up_among_the_choices_as_a_pair(admin_ui, superuser, category):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert (str(category.pk), "Tools") in page.fields["category"].choices


def test_the_choice_made_is_one_of_the_choices(admin_ui, editor, released):
    admin_ui.login(editor)

    page = admin_ui.edit(released)

    field = page.fields["category"]
    assert field.value in field.choices


def test_a_field_without_options_offers_no_choices(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert page.fields["name"].choices == []
    assert page.fields["is_active"].choices == []


def test_a_rendered_only_field_offers_no_choices(admin_ui, viewer, released):
    admin_ui.login(viewer)

    page = admin_ui.edit(released)

    assert page.fields["category"].choices == []
