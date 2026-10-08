"""The rules that read what the admin renders, replaced by a project."""

import datetime

import pytest

from django_admin_kit.normalize import DEFAULTS, Normalizers
from project.shop import rules
from project.shop.models import Feed, Product


@pytest.fixture(scope="session")
def admin_ui_normalizers():
    """Every rule replaced by one that says which rule read the value, the way a project
    overrides the fixture for some of its tests."""
    return Normalizers({name: getattr(rules, name) for name in DEFAULTS})


@pytest.fixture
def refreshed(feed):
    """The feed, with the date-time it was refreshed at and the time of day it refreshes."""
    feed.refreshed_at = datetime.datetime(2026, 1, 15, 9, 30, tzinfo=datetime.timezone.utc)
    feed.refresh_time = datetime.time(6, 0)
    feed.save()
    return feed


@pytest.fixture
def listing(admin_ui, viewer, products):
    """The product changelist, as a user who may only view reads it."""
    admin_ui.login(viewer)
    return admin_ui.list(Product)


@pytest.fixture
def feed_row(admin_ui, superuser, refreshed):
    """The refreshed feed's row on the feed changelist."""
    admin_ui.login(superuser)
    return admin_ui.list(Feed).rows[0]


def test_a_cell_drawn_as_text_is_read_by_the_text_rule(listing):
    row = listing.rows[0]

    assert row["name"].value == ("text", "Bolt")
    assert row["sku"].value == ("text", "SKU-Bolt")


def test_a_cell_drawn_as_a_boolean_icon_is_read_by_the_boolean_rule(listing):
    row = listing.rows[0]

    assert row["is_active"].value == ("boolean", "True")
    assert row["featured"].value == ("boolean", "None")


def test_a_bool_the_admin_renders_as_text_is_read_by_the_text_rule(listing):
    """`is_released` is a method that does not ask for the icon."""
    assert listing.rows[0]["is_released"].value == ("text", "False")


def test_a_field_the_user_may_only_read_is_read_by_the_rules(admin_ui, viewer, product):
    admin_ui.login(viewer)

    page = admin_ui.edit(product)

    assert page.fields["name"].value == ("text", "Widget")
    assert page.fields["is_active"].value == ("boolean", "True")


def test_an_editable_field_reads_its_control_through_no_rule(admin_ui, superuser, product):
    admin_ui.login(superuser)

    page = admin_ui.edit(product)

    assert page.fields["name"].value == "Widget"
    assert page.fields["is_active"].value is True


def test_the_page_a_submission_leads_to_reads_through_the_same_rules(admin_ui, superuser, released):
    """Uses the released product, because the form requires a release date."""
    admin_ui.login(superuser)

    result = admin_ui.edit(released).save()

    assert result.page.rows[0]["name"].value == ("text", "Widget")


def test_a_number_field_is_read_by_the_number_rule(listing):
    assert listing.rows[0]["price"].value == ("number", "10.00")


def test_a_date_field_is_read_by_the_date_rule(admin_ui, viewer, released):
    admin_ui.login(viewer)

    row = admin_ui.list(Product).rows[0]

    assert row["released_on"].value == ("date", "Jan. 15, 2026")


def test_a_date_time_field_is_read_by_the_date_time_rule(feed_row):
    """Django makes a date-time field a kind of date field; the more specific rule reads it."""
    assert feed_row["refreshed_at"].value == ("datetime", "Jan. 15, 2026, 9:30 a.m.")


def test_a_time_field_is_read_by_the_time_rule(feed_row):
    assert feed_row["refresh_time"].value == ("time", "6 a.m.")


def test_a_field_with_choices_is_read_by_the_choice_rule_as_its_label(feed_row):
    assert feed_row["mode"].value == ("choice", "Append")


def test_a_method_drawn_as_a_boolean_icon_is_read_by_the_boolean_rule(feed_row):
    """`refreshed` is a method; only its icon says it is a boolean."""
    assert feed_row["refreshed"].value == ("boolean", "True")


def test_a_field_the_user_may_only_read_is_read_by_its_fields_rule(admin_ui, viewer, released):
    admin_ui.login(viewer)

    page = admin_ui.edit(released)

    assert page.fields["released_on"].value == ("date", "Jan. 15, 2026")
    assert page.fields["quantity"].value == ("number", "1")


def test_a_value_knows_the_model_field_behind_it(listing):
    row = listing.rows[0]

    assert row["price"].field == Product._meta.get_field("price")
    assert row["price_with_tax"].field is None
