"""Putting values into the fields of a create or edit page, one at a time or in one call."""

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


def test_a_dictionary_fills_the_fields_it_names(admin_ui, superuser, category):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)
    page.populate(
        {
            "name": "Widget",
            "sku": "SKU-1",
            "price": "19.99",
            "quantity": 3,
            "is_active": False,
            "featured": True,
            "released_on": datetime.date(2026, 1, 15),
            "category": str(category.pk),
        }
    )

    assert page.fields["name"].value == "Widget"
    assert page.fields["sku"].value == "SKU-1"
    assert page.fields["price"].value == "19.99"
    assert page.fields["quantity"].value == "3"
    assert page.fields["is_active"].value is False
    assert page.fields["featured"].value == YES
    assert page.fields["released_on"].value == "2026-01-15"
    assert page.fields["category"].value == (str(category.pk), "Tools")


def test_a_change_page_takes_a_new_value_for_every_field(admin_ui, editor, product, category):
    """The form comes with the record's own values, and populating replaces each one it
    names rather than adding to it."""
    admin_ui.login(editor)

    page = admin_ui.edit(product)
    page.populate(
        {
            "name": "Gadget",
            "sku": "SKU-2",
            "price": "24.50",
            "quantity": 7,
            "is_active": False,
            "featured": True,
            "released_on": datetime.date(2026, 3, 1),
            "category": str(category.pk),
        }
    )

    assert page.fields["name"].value == "Gadget"
    assert page.fields["sku"].value == "SKU-2"
    assert page.fields["price"].value == "24.50"
    assert page.fields["quantity"].value == "7"
    assert page.fields["is_active"].value is False
    assert page.fields["featured"].value == YES
    assert page.fields["released_on"].value == "2026-03-01"
    assert page.fields["category"].value == (str(category.pk), "Tools")


def test_a_field_the_dictionary_does_not_name_stays_as_the_page_rendered_it(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)
    page.populate({"name": "Widget"})

    assert page.fields["quantity"].value == "1"
    assert page.fields["is_active"].value is True
    assert page.fields["featured"].value == UNKNOWN
    assert page.fields["released_on"].value == ""
    assert page.fields["category"].value == BLANK


def test_a_key_the_form_has_no_field_for_is_ignored(admin_ui, superuser):
    """A misspelt name fills nothing; the test fails on what it asserts next."""
    admin_ui.login(superuser)

    page = admin_ui.create(Product)
    page.populate({"colour": "red", "name": "Widget"})

    assert page.fields["name"].value == "Widget"
    assert "colour" not in page.fields


def test_a_rendered_only_field_is_passed_over(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)
    page.populate({"price_with_tax": "99.00", "name": "Widget"})

    assert page.fields["price_with_tax"].value == "(none)"
    assert page.fields["name"].value == "Widget"


def test_keywords_alone_fill_the_fields_they_name(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)
    page.populate(name="Widget", quantity=3)

    assert page.fields["name"].value == "Widget"
    assert page.fields["quantity"].value == "3"


def test_a_keyword_wins_over_the_dictionary_for_the_same_field(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)
    page.populate({"name": "Widget", "sku": "SKU-1"}, name="Gadget")

    assert page.fields["name"].value == "Gadget"
    assert page.fields["sku"].value == "SKU-1"


def test_a_keyword_adds_a_field_the_dictionary_lacks(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)
    page.populate({"name": "Widget"}, is_active=False)

    assert page.fields["name"].value == "Widget"
    assert page.fields["is_active"].value is False


def test_a_keyword_the_form_has_no_field_for_is_ignored(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)
    page.populate(colour="red", name="Widget")

    assert page.fields["name"].value == "Widget"
    assert "colour" not in page.fields


def test_a_viewer_has_nothing_to_populate(admin_ui, viewer, product):
    admin_ui.login(viewer)

    page = admin_ui.edit(product)
    page.populate({"name": "Gadget"})

    assert page.fields["name"].value == "Widget"


def test_a_form_that_did_not_open_has_nothing_to_populate(admin_ui, viewer):
    admin_ui.login(viewer)

    page = admin_ui.create(Product)

    with pytest.raises(LookupError, match=r"did not open.*Status 403"):
        page.populate({"name": "Widget"})
