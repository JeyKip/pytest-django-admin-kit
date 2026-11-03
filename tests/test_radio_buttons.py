"""Radio buttons, as the admin draws a field named in `radio_fields`: read as the option
checked and filled with the option for a value, as a select is."""

import pytest

from django_admin_kit.widgets import Widgets
from project.shop.kit_widgets import SwatchPickerWidget
from project.shop.models import Category, Feed

# The feed's mode as the radio buttons offer it, by value and label. It has a default, so
# the admin draws no blank option.
APPEND = ("append", "Append")
REPLACE = ("replace", "Replace")

# The option the admin adds for a section that may be empty.
NO_SECTION = ("", "None")


@pytest.fixture(scope="session")
def admin_ui_widgets():
    """The swatch picker's widget class, so populating a whole feed can fill its color."""
    return Widgets([SwatchPickerWidget()])


@pytest.fixture
def tools(db):
    return Category.objects.create(name="Tools")


def test_radio_buttons_read_as_the_choice_checked(admin_ui, superuser, tools):
    feed = Feed.objects.create(source="catalog.csv", mode="replace", section=tools)
    admin_ui.login(superuser)

    page = admin_ui.edit(feed)

    assert page.fields["mode"].value == REPLACE
    assert page.fields["mode"].value.label == "Replace"
    assert page.fields["section"].value == (str(tools.pk), "Tools")
    assert page.fields["section"].value.label == "Tools"


def test_radio_buttons_with_none_checked_read_as_none(admin_ui, superuser):
    """The admin always checks one: the mode's default, Append, on a create page. A script
    or the browser's own state can leave none checked, so the test unchecks it."""
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)

    page.fields["mode"].native.locator("input:checked").evaluate("radio => radio.checked = false")

    assert page.fields["mode"].value is None


def test_radio_buttons_are_filled_with_an_option_value(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)

    page.fields["mode"].fill("replace")

    assert page.fields["mode"].value == REPLACE


def test_radio_buttons_are_filled_with_a_field_choice(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)

    page.fields["mode"].fill(page.fields["mode"].choices[1])

    assert page.fields["mode"].value == REPLACE


@pytest.mark.parametrize(
    "spelling",
    [
        lambda category: category,
        lambda category: category.pk,
        lambda category: str(category.pk),
    ],
    ids=["model instance", "primary key", "primary key as text"],
)
def test_radio_buttons_of_objects_are_filled_with_one_of_them(admin_ui, superuser, tools, spelling):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)

    page.fields["section"].fill(spelling(tools))

    assert page.fields["section"].value == (str(tools.pk), "Tools")


def test_none_checks_the_blank_radio_button(admin_ui, superuser, tools):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)
    page.fields["section"].fill(tools)

    page.fields["section"].fill(None)

    assert page.fields["section"].value == NO_SECTION


def test_none_is_refused_without_a_blank_radio_button(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)

    with pytest.raises(ValueError) as failure:
        page.fields["mode"].fill(None)

    assert str(failure.value) == (
        "The field 'mode' offers no option for None. Options: 'append', 'replace'."
    )


def test_a_value_radio_buttons_do_not_offer_is_refused(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)

    with pytest.raises(ValueError) as failure:
        page.fields["mode"].fill("merge")

    assert str(failure.value) == (
        "The field 'mode' offers no option for 'merge'. Options: 'append', 'replace'."
    )
    assert page.fields["mode"].value == APPEND


def test_radio_buttons_offer_their_options_as_choices(admin_ui, superuser, tools):
    admin_ui.login(superuser)

    page = admin_ui.create(Feed)

    assert page.fields["mode"].choices == [APPEND, REPLACE]
    assert page.fields["section"].choices == [NO_SECTION, (str(tools.pk), "Tools")]


def test_populate_fills_radio_buttons_from_a_saved_instance(admin_ui, superuser, tools):
    other = Feed.objects.create(source="other.csv", mode="replace", section=tools)
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)

    page.populate(other)

    assert page.fields["mode"].value == REPLACE
    assert page.fields["section"].value == (str(tools.pk), "Tools")


def test_checked_radio_buttons_are_stored(admin_ui, superuser, tools):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)
    page.populate(source="catalog.csv", mode="replace", section=tools)

    assert page.save().success

    feed = Feed.objects.get()
    assert feed.mode == "replace"
    assert feed.section == tools


def test_a_rejected_save_renders_back_the_radio_button_checked(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)
    page.populate(source="", mode="replace")

    result = page.save()

    assert not result.success
    assert result.page.fields["mode"].value == REPLACE
