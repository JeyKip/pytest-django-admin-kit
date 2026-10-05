"""The validation errors a create or edit page shows once the admin has rejected it."""

import datetime

import pytest

from project.shop.models import Product

# Every field the product form requires but the release date, so the admin rejects the
# form for that one field.
UNRELEASED = {
    "name": "Widget",
    "sku": "SKU-1",
    "price": "10.00",
}

# A product the form accepts field by field, but rejects as a whole: it is featured
# without being active.
FEATURED_INACTIVE = {
    "name": "Widget",
    "sku": "SKU-1",
    "price": "10.00",
    "released_on": datetime.date(2026, 1, 15),
    "is_active": False,
    "featured": True,
}


@pytest.fixture
def creating(admin_ui, superuser):
    """A product's create page, not yet filled in."""
    admin_ui.login(superuser)
    return admin_ui.create(Product)


def test_a_page_never_submitted_shows_no_errors(creating):
    errors = creating.errors

    assert not errors
    assert errors.banner == ""
    assert errors.non_field == []
    assert errors.fields == {}


def test_a_form_rejected_for_several_fields_says_so_in_its_notice(creating):
    creating.populate(name="Widget")

    result = creating.save()

    assert result.page.errors
    assert result.page.errors.banner == "Please correct the errors below."


def test_a_form_rejected_for_one_field_says_so_in_its_notice(creating):
    creating.populate(UNRELEASED)

    result = creating.save()

    assert result.page.errors.banner == "Please correct the error below."


def test_an_edit_page_shows_the_same_notice(admin_ui, superuser, released):
    admin_ui.login(superuser)
    page = admin_ui.edit(released)
    page.populate(name="")

    result = page.save()

    assert result.page.errors.banner == "Please correct the error below."


def test_a_form_rejected_as_a_whole_lists_its_error_apart_from_the_notice(creating):
    creating.populate(FEATURED_INACTIVE)

    result = creating.save()

    assert result.page.errors.non_field == ["A featured product must be active."]
    assert result.page.errors.banner == "Please correct the error below."


def test_errors_held_from_before_a_rejection_read_the_rejected_form(creating):
    errors = creating.errors
    creating.populate(UNRELEASED)

    creating.save()

    assert errors.banner == "Please correct the error below."
    assert errors.non_field == []


def test_a_refused_page_has_no_errors_to_read(admin_ui, viewer):
    admin_ui.login(viewer)
    page = admin_ui.create(Product)

    with pytest.raises(LookupError) as failure:
        bool(page.errors)

    assert str(failure.value) == (
        "The page did not open, so there is nothing to read from it. "
        f"Status 403, at {admin_ui.url.create(Product)}."
    )


def test_each_field_of_an_empty_form_reads_its_own_errors(creating):
    """The quantity starts with a value and the rest are optional, so only the empty
    required fields have errors. The price with tax is rendered only."""
    result = creating.save()

    fields = result.page.fields
    assert fields["name"].errors == ["This field is required."]
    assert fields["sku"].errors == ["This field is required."]
    assert fields["price"].errors == ["This field is required."]
    assert fields["quantity"].errors == []
    assert fields["is_active"].errors == []
    assert fields["featured"].errors == []
    assert fields["released_on"].errors == ["This field is required."]
    assert fields["category"].errors == []
    assert fields["price_with_tax"].errors == []


def test_a_field_with_several_errors_reads_them_all_in_order(creating):
    creating.populate(UNRELEASED, sku="bad sku")

    result = creating.save()

    assert result.page.fields["sku"].errors == [
        'A SKU must start with "SKU-".',
        "A SKU must not contain spaces.",
    ]


def test_a_field_sharing_its_line_reads_only_its_own_errors(creating):
    """The sku and the price share a line, where Django 4.2 to 6.0 put each field's
    errors outside its box."""
    creating.populate(UNRELEASED, sku="")

    result = creating.save()

    assert result.page.fields["sku"].errors == ["This field is required."]
    assert result.page.fields["price"].errors == []


def test_an_edit_page_reads_its_field_errors_the_same_way(admin_ui, superuser, released, products):
    admin_ui.login(superuser)
    page = admin_ui.edit(released)
    page.populate(sku="SKU-Bolt")

    result = page.save()

    assert result.page.fields["sku"].errors == ["Product with this Sku already exists."]


def test_the_errors_of_every_field_are_read_at_once(creating):
    creating.populate(name="Widget")

    result = creating.save()

    assert result.page.errors.fields == {
        "sku": ["This field is required."],
        "price": ["This field is required."],
        "released_on": ["This field is required."],
    }


def test_a_field_held_from_before_a_rejection_reads_its_errors(creating):
    field = creating.fields["name"]

    creating.save()

    assert field.errors == ["This field is required."]
