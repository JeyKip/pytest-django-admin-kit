"""Putting values into the fields of a create or edit page, one field at a time."""

import datetime
from decimal import Decimal

import django
import pytest

from django_admin_kit.fields import FieldChoice
from project.shop.models import Product

# The option a select shows for no choice. Django 6.1 reworded it; the package works from
# the option's value, which is `""` on every version, so the suite proves both wordings.
BLANK = ("", "- Select an option -" if django.VERSION >= (6, 1) else "---------")

# What the widget of a nullable boolean offers, by the value it posts.
YES = ("true", "Yes")
NO = ("false", "No")
UNKNOWN = ("unknown", "Unknown")


def test_a_text_control_takes_the_text(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)
    page.fields["name"].fill("Widget")

    assert page.fields["name"].value == "Widget"


def test_a_number_control_takes_a_number_as_the_text_it_shows(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)
    page.fields["price"].fill(Decimal("19.99"))

    assert page.fields["price"].value == "19.99"


def test_a_date_control_takes_a_date_as_the_text_it_shows(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)
    page.fields["released_on"].fill(datetime.date(2026, 1, 15))

    assert page.fields["released_on"].value == "2026-01-15"


def test_a_text_control_is_emptied_by_none(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)
    page.fields["name"].fill("Widget")
    page.fields["name"].fill(None)

    assert page.fields["name"].value == ""


@pytest.mark.parametrize("value", [True, False])
def test_a_checkbox_takes_a_boolean(admin_ui, superuser, value):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)
    # Put the box on the other state first, so filling it has something to change.
    page.fields["is_active"].fill(not value)
    page.fields["is_active"].fill(value)

    assert page.fields["is_active"].value is value


@pytest.mark.parametrize(("value", "checked"), [(1, True), (0, False)])
def test_a_checkbox_follows_the_truth_of_what_it_is_given(admin_ui, superuser, value, checked):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)
    page.fields["is_active"].fill(not checked)
    page.fields["is_active"].fill(value)

    assert page.fields["is_active"].value is checked


def test_a_select_takes_the_value_of_one_of_its_options(admin_ui, superuser, category):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)
    page.fields["category"].fill(str(category.pk))

    assert page.fields["category"].value == (str(category.pk), "Tools")


def test_a_select_takes_a_choice_it_offers(admin_ui, superuser, category):
    """What `choices` gives back goes straight back in, without taking it apart."""
    admin_ui.login(superuser)

    page = admin_ui.create(Product)
    tools = page.fields["category"].choices[-1]
    page.fields["category"].fill(tools)

    assert tools == FieldChoice(str(category.pk), "Tools")
    assert page.fields["category"].value == tools


def test_a_select_is_put_back_to_its_blank_option_by_none(admin_ui, superuser, category):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)
    page.fields["category"].fill(str(category.pk))
    page.fields["category"].fill(None)

    assert page.fields["category"].value == BLANK


@pytest.mark.parametrize(
    ("value", "chosen"),
    [(True, YES), (False, NO), (None, UNKNOWN)],
)
def test_a_nullable_boolean_select_takes_a_python_boolean(admin_ui, superuser, value, chosen):
    """Django spells this widget's three options `true`, `false` and `unknown`, so a
    boolean is not the text of its option; the field is given one all the same."""
    admin_ui.login(superuser)

    page = admin_ui.create(Product)
    page.fields["featured"].fill(value)

    assert page.fields["featured"].value == chosen


def test_a_value_no_option_has_is_reported_with_the_options_offered(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    with pytest.raises(ValueError) as failure:
        page.fields["featured"].fill("maybe")
    assert str(failure.value) == (
        "The field 'featured' offers no option for 'maybe'. Options: 'unknown', 'true', 'false'."
    )


def test_a_rendered_only_field_has_nothing_to_fill(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    with pytest.raises(LookupError) as failure:
        page.fields["price_with_tax"].fill("12.00")
    assert str(failure.value) == (
        "The field 'price_with_tax' is rendered only, so there is nothing to fill."
    )


def test_a_viewer_has_no_field_to_fill(admin_ui, viewer, product):
    """A user who may only view gets every field rendered only, so none of them takes
    a value, not even the ones an editor would type into."""
    admin_ui.login(viewer)

    page = admin_ui.edit(product)

    for name in page.fields:
        with pytest.raises(LookupError, match="is rendered only"):
            page.fields[name].fill("Gadget")
