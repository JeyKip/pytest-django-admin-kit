"""The rules that read what the admin renders, replaced by a project."""

import pytest

from django_admin_kit.normalize import Normalizers
from project.shop import rules
from project.shop.models import Product


@pytest.fixture(scope="session")
def admin_ui_normalizers():
    """Every rule replaced by one that says which rule read the value, the way a project
    overrides the fixture for some of its tests."""
    return Normalizers({"boolean": rules.boolean, "text": rules.text})


@pytest.fixture
def listing(admin_ui, viewer, products):
    """The product changelist, as a user who may only view reads it."""
    admin_ui.login(viewer)
    return admin_ui.list(Product)


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
