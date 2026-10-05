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
    assert not creating.errors


def test_a_page_never_submitted_shows_no_notice(creating):
    assert creating.errors.banner == ""


def test_a_page_never_submitted_shows_no_form_level_errors(creating):
    assert creating.errors.non_field == []


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
