"""The fieldsets a create or edit page draws its fields in, in the admin's order."""

import pytest

from project.shop.models import Feed, Product

# The name of the feed's last fieldset, as the user reads it. The admin gives it markup,
# which the user doesn't see.
APPEARANCE = "Appearance on the page"

# The description of the feed's "Schedule" fieldset, as the user reads it. The admin
# gives it markup, which the user doesn't see.
SCHEDULE_DESCRIPTION = "When the feed last ran, and the time it runs each day."

# The product form as the admin lays it out. Its admin sets `fields`, not `fieldsets`, and
# the hidden `source` field is on the page but never shown.
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


def test_the_fieldsets_are_listed_in_the_admin_order_with_their_names(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Feed)

    assert [fieldset.name for fieldset in page.fieldsets] == [None, "Schedule", APPEARANCE]


def test_a_name_is_read_without_its_markup(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Feed)

    assert page.fieldsets[2].name == APPEARANCE


def test_each_fieldset_holds_its_fields_in_order(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Feed)

    assert [list(fieldset.fields) for fieldset in page.fieldsets] == [
        ["source", "mode"],
        ["refreshed_at", "refresh_time"],
        ["color"],
    ]


def test_a_description_is_read_without_its_markup(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Feed)

    assert page.fieldsets[1].description == SCHEDULE_DESCRIPTION


def test_a_fieldset_without_a_description_reads_as_none(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Feed)

    assert page.fieldsets[0].description is None
    assert page.fieldsets[2].description is None


def test_the_fieldsets_hold_the_form_fields_in_order(admin_ui, superuser, feed):
    admin_ui.login(superuser)

    page = admin_ui.edit(feed)

    names = [name for fieldset in page.fieldsets for name in fieldset.fields]
    assert names == list(page.fields)


def test_a_field_is_read_and_filled_through_its_fieldset(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)

    page.fieldsets[0].fields["source"].fill("catalog.csv")

    assert page.fieldsets[0].fields["source"].value == "catalog.csv"
    assert page.fields["source"].value == "catalog.csv"


def test_a_field_the_fieldset_does_not_have_is_reported_with_the_ones_it_has(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)

    with pytest.raises(KeyError) as failure:
        page.fieldsets[0].fields["color"]

    assert failure.value.args[0] == "No field named 'color' here. Fields: 'source', 'mode'."


def test_a_form_without_fieldsets_is_one_unnamed_fieldset(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert len(page.fieldsets) == 1
    assert page.fieldsets[0].name is None
    assert page.fieldsets[0].description is None
    assert list(page.fieldsets[0].fields) == FIELDS


def test_a_fieldset_is_its_fieldset_element(admin_ui, superuser):
    """Anything the package does not model is reached through it."""
    admin_ui.login(superuser)

    page = admin_ui.create(Feed)

    assert page.fieldsets[1].native.evaluate("element => element.tagName") == "FIELDSET"
    assert page.fieldsets[1].native.locator("[name=refresh_time]").count() == 1
