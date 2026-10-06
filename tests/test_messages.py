"""The messages the admin shows after an operation, read from the page it leads to."""

import datetime

import pytest

from project.shop.models import Product

# Every field the product form requires, so the admin accepts the save.
WIDGET = {
    "name": "Widget",
    "sku": "SKU-1",
    "price": "10.00",
    "released_on": datetime.date(2026, 1, 15),
}

ADDED = "The product “Widget” was added successfully."


@pytest.fixture
def saved(admin_ui, superuser):
    """The result of adding a product the admin accepts."""
    admin_ui.login(superuser)
    page = admin_ui.create(Product)
    page.populate(WIDGET)
    return page.save()


def test_a_page_opened_directly_shows_no_messages(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert not page.messages
    assert page.messages == []


def test_an_accepted_save_leads_to_a_page_that_says_so(saved):
    assert saved.page.messages == [("success", ADDED)]


def test_a_message_has_its_level_and_its_text(saved):
    message = saved.page.messages[0]

    assert message.level == "success"
    assert message.text == ADDED


def test_a_message_equals_its_pair_written_either_way_but_not_its_text(saved):
    message = saved.page.messages[0]

    assert message == ("success", ADDED)
    assert message == ["success", ADDED]
    assert message != ADDED


def test_continuing_shows_the_message_on_the_same_page(admin_ui, superuser, released):
    """Uses the released product, because the form requires a release date."""
    admin_ui.login(superuser)
    page = admin_ui.edit(released)
    page.populate(name="Gadget")

    result = page.save_and_continue()

    assert result.page is page
    assert page.messages == [
        ("success", "The product “Gadget” was changed successfully. You may edit it again below.")
    ]


def test_a_confirmed_deletion_says_so_on_the_changelist(admin_ui, superuser, product):
    admin_ui.login(superuser)

    result = admin_ui.delete(product).confirm_deleting()

    assert result.page.messages == [("success", "The product “Widget” was deleted successfully.")]


def test_a_rejected_form_shows_errors_and_no_messages(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Product)
    page.populate(name="Widget")

    result = page.save()

    assert result.page.errors
    assert result.page.messages == []


def test_a_missing_object_reads_the_warning_the_index_shows_for_it(admin_ui, superuser, product):
    """The page did not open, but the index it landed on says why."""
    Product.objects.filter(pk=product.pk).delete()
    admin_ui.login(superuser)

    page = admin_ui.edit(product)

    assert page.missing
    # The admin's text has a typographic apostrophe, which the check for look-alike
    # characters would otherwise flag.
    assert page.messages == [
        ("warning", f"Product with ID “{product.pk}” doesn’t exist. Perhaps it was deleted?")  # noqa: RUF001
    ]


def test_a_page_refused_in_place_reads_no_messages(admin_ui, viewer):
    admin_ui.login(viewer)

    page = admin_ui.create(Product)

    assert page.denied
    assert page.messages == []
