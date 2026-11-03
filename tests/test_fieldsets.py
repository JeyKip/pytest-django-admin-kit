"""The fieldsets a create or edit page draws its fields in, in the admin's order, and
the ones the user may collapse."""

import datetime

import pytest

from project.shop.models import Category, Feed, Product

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
        ["source", "mode", "section"],
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

    assert failure.value.args[0] == (
        "No field named 'color' here. Fields: 'source', 'mode', 'section'."
    )


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


def test_only_the_fieldset_the_admin_lets_collapse_is_collapsible(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Feed)

    assert [fieldset.collapsible for fieldset in page.fieldsets] == [False, True, False]


def test_a_collapsible_fieldset_starts_collapsed(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Feed)

    assert [fieldset.collapsed for fieldset in page.fieldsets] == [False, True, False]


def test_a_collapsed_fieldset_keeps_its_name(admin_ui, superuser):
    """Before Django 5.1 the admin's script adds a "Show" link to the name, then "Hide"."""
    admin_ui.login(superuser)
    schedule = admin_ui.create(Feed).fieldsets[1]

    collapsed_name = schedule.name
    schedule.open()

    assert collapsed_name == "Schedule"
    assert schedule.name == "Schedule"


def test_the_fields_of_a_collapsed_fieldset_are_read_without_opening_it(admin_ui, superuser):
    admin_ui.login(superuser)
    schedule = admin_ui.create(Feed).fieldsets[1]

    field = schedule.fields["refresh_time"]

    assert field.label == "Refresh time"
    assert field.value == ""
    assert schedule.collapsed


def test_filling_a_field_of_a_collapsed_fieldset_opens_it(admin_ui, superuser):
    admin_ui.login(superuser)
    schedule = admin_ui.create(Feed).fieldsets[1]

    schedule.fields["refresh_time"].fill("06:00:00")

    assert schedule.fields["refresh_time"].value == "06:00:00"
    assert not schedule.collapsed
    assert schedule.collapsible


def test_closing_and_opening_a_fieldset_follows_its_toggle(admin_ui, superuser):
    admin_ui.login(superuser)
    schedule = admin_ui.create(Feed).fieldsets[1]
    schedule.open()

    schedule.close()
    closed = schedule.collapsed
    schedule.open()

    assert closed
    assert not schedule.collapsed


def test_opening_or_closing_a_fieldset_twice_changes_nothing(admin_ui, superuser):
    admin_ui.login(superuser)
    schedule = admin_ui.create(Feed).fieldsets[1]

    schedule.open()
    schedule.open()
    opened = not schedule.collapsed
    schedule.close()
    schedule.close()

    assert opened
    assert schedule.collapsed


def test_a_fieldset_without_a_toggle_cannot_be_opened_or_closed(admin_ui, superuser):
    admin_ui.login(superuser)
    appearance = admin_ui.create(Feed).fieldsets[2]

    with pytest.raises(LookupError) as opening:
        appearance.open()
    with pytest.raises(LookupError) as closing:
        appearance.close()

    assert str(opening.value) == (
        f"The fieldset {APPEARANCE!r} cannot be opened: the page offers no toggle for it."
    )
    assert str(closing.value) == (
        f"The fieldset {APPEARANCE!r} cannot be closed: the page offers no toggle for it."
    )


def test_a_fieldset_without_a_name_cannot_be_opened(admin_ui, superuser):
    admin_ui.login(superuser)
    first = admin_ui.create(Feed).fieldsets[0]

    with pytest.raises(LookupError) as failure:
        first.open()

    assert str(failure.value) == (
        "A fieldset without a name cannot be opened: the page offers no toggle for it."
    )


def test_populate_fills_a_collapsed_fieldset_and_the_save_stores_it(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)
    page.populate(source="catalog.csv", refresh_time="06:00:00")

    assert page.save().success

    assert Feed.objects.get().refresh_time == datetime.time(6, 0)


def test_a_fieldset_with_an_error_is_shown_open_without_a_toggle(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)
    page.populate(source="catalog.csv", refresh_time="soon")

    result = page.save()

    schedule = result.page.fieldsets[1]
    assert result.page.fields["refresh_time"].errors == ["Enter a valid time."]
    assert not schedule.collapsed
    assert not schedule.collapsible


def test_a_field_no_widget_class_can_fill_leaves_its_fieldset_collapsed(admin_ui, superuser):
    """The category's shelf is two inputs drawn by a widget of the project's own, which no
    built-in widget class fills."""
    admin_ui.login(superuser)
    placement = admin_ui.create(Category).fieldsets[1]

    with pytest.raises(LookupError):
        placement.fields["shelf"].fill(["3", "B"])

    assert placement.collapsed
