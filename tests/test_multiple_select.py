"""A multiple select, as the admin draws a many-to-many field: read as the choices made,
in the order offered, and filled with exactly the options for a list of values."""

import pytest

from django_admin_kit.widgets import Widgets
from project.shop.kit_widgets import SwatchPickerWidget
from project.shop.models import Category, Feed


@pytest.fixture(scope="session")
def admin_ui_widgets():
    """The swatch picker's widget class, so populating a whole feed can fill its color."""
    return Widgets([SwatchPickerWidget()])


@pytest.fixture
def tools(db):
    return Category.objects.create(name="Tools")


@pytest.fixture
def toys(db):
    return Category.objects.create(name="Toys")


def test_a_multiple_select_reads_as_the_choices_made_in_order(admin_ui, superuser, tools, toys):
    """The options are in the categories' order, by name, whatever order they were added in."""
    feed = Feed.objects.create(source="catalog.csv")
    feed.categories.set([toys, tools])
    admin_ui.login(superuser)

    page = admin_ui.edit(feed)

    assert page.fields["categories"].value == [(str(tools.pk), "Tools"), (str(toys.pk), "Toys")]
    assert [choice.label for choice in page.fields["categories"].value] == ["Tools", "Toys"]


def test_a_multiple_select_with_nothing_chosen_reads_as_empty(admin_ui, superuser, tools):
    admin_ui.login(superuser)

    page = admin_ui.create(Feed)

    assert page.fields["categories"].value == []


def test_a_multiple_select_is_filled_with_exactly_the_values_given(
    admin_ui, superuser, tools, toys
):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)
    page.fields["categories"].fill([tools, toys])

    page.fields["categories"].fill([toys])

    assert page.fields["categories"].value == [(str(toys.pk), "Toys")]


def test_a_multiple_select_is_filled_with_option_values(admin_ui, superuser, tools, toys):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)

    page.fields["categories"].fill([tools.pk, str(toys.pk)])

    assert page.fields["categories"].value == [(str(tools.pk), "Tools"), (str(toys.pk), "Toys")]


def test_a_multiple_select_is_filled_with_its_own_choices(admin_ui, superuser, tools, toys):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)

    page.fields["categories"].fill(page.fields["categories"].choices)

    assert page.fields["categories"].value == [(str(tools.pk), "Tools"), (str(toys.pk), "Toys")]


@pytest.mark.parametrize("empty", [None, []], ids=["none", "empty list"])
def test_none_and_an_empty_list_clear_a_multiple_select(admin_ui, superuser, tools, toys, empty):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)
    page.fields["categories"].fill([tools, toys])

    page.fields["categories"].fill(empty)

    assert page.fields["categories"].value == []


@pytest.mark.parametrize(
    "lone",
    [lambda category: str(category.pk), lambda category: category, lambda category: category.pk],
    ids=["text", "model instance", "number"],
)
def test_a_lone_value_is_refused_for_a_multiple_select(admin_ui, superuser, tools, lone):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)
    value = lone(tools)

    with pytest.raises(TypeError) as failure:
        page.fields["categories"].fill(value)

    assert str(failure.value) == (
        f"The field 'categories' takes a list of values or None, not {value!r}. "
        f"A single value is written as [value]."
    )


def test_a_value_a_multiple_select_does_not_offer_is_refused(admin_ui, superuser, tools, toys):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)

    with pytest.raises(ValueError) as failure:
        page.fields["categories"].fill([tools, "Games"])

    assert str(failure.value) == (
        f"The field 'categories' offers no option for 'Games'. Options: '{tools.pk}', '{toys.pk}'."
    )
    assert page.fields["categories"].value == []


def test_a_multiple_select_offers_its_options_as_choices(admin_ui, superuser, tools, toys):
    admin_ui.login(superuser)

    page = admin_ui.create(Feed)

    assert page.fields["categories"].choices == [
        (str(tools.pk), "Tools"),
        (str(toys.pk), "Toys"),
    ]


def test_populate_fills_a_many_to_many_field_from_a_saved_instance(
    admin_ui, superuser, tools, toys
):
    other = Feed.objects.create(source="other.csv")
    other.categories.set([toys])
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)

    page.populate(other)

    assert page.fields["categories"].value == [(str(toys.pk), "Toys")]


def test_populate_leaves_a_many_to_many_field_alone_for_an_unsaved_instance(
    admin_ui, superuser, tools
):
    """An unsaved feed has no categories yet, so the ones already chosen stay."""
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)
    page.fields["categories"].fill([tools])

    page.populate(Feed(source="catalog.csv"))

    assert page.fields["source"].value == "catalog.csv"
    assert page.fields["categories"].value == [(str(tools.pk), "Tools")]


def test_a_saved_multiple_select_is_stored(admin_ui, superuser, tools, toys):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)
    page.populate(source="catalog.csv", categories=[tools, toys])

    assert page.save().success

    assert list(Feed.objects.get().categories.all()) == [tools, toys]
