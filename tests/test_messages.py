"""The messages the admin shows after an operation, read from the page it leads to."""

import datetime

import pytest
from django.contrib.messages.storage import base
from django.contrib.messages.utils import get_level_tags

from project.shop.models import Feed, Product

# Every field the product form requires, so the admin accepts the save.
WIDGET = {
    "name": "Widget",
    "sku": "SKU-1",
    "price": "10.00",
    "released_on": datetime.date(2026, 1, 15),
}

ADDED = "The product “Widget” was added successfully."

# What the feed's own admin says about a source that is no CSV file, and one with spaces.
NOT_CSV = "The source should be a CSV file."
SPACES = "The source should not contain spaces."


@pytest.fixture
def message_tags(settings, monkeypatch):
    """Set the project's `MESSAGE_TAGS` for one test, as its `settings.py` would.

    `MESSAGE_TAGS` is the project's setting: only the tags it adds or renames. Django
    renders every message from `LEVEL_TAGS`, its own defaults with that setting merged in,
    kept as a module global. Django 4.1 and later rebuild that global when the setting
    changes; Django 3.2 and 4.0 build it once, at import, and would keep rendering the old
    tags. So this also rebuilds it, which is what Django's own tests do, and pytest puts
    both back after the test. It is needed only because a test changes the setting in the
    middle of a run; a project that sets `MESSAGE_TAGS` in `settings.py` needs nothing.
    """

    def use(tags):
        settings.MESSAGE_TAGS = tags
        monkeypatch.setattr(base, "LEVEL_TAGS", get_level_tags())

    return use


@pytest.fixture
def adding_feed(admin_ui, superuser):
    """A feed's create page, not yet filled in."""
    admin_ui.login(superuser)
    return admin_ui.create(Feed)


@pytest.fixture
def refreshing_feed(admin_ui, superuser, feed):
    """A feed's edit page, ready for the project's own "Refresh" button."""
    admin_ui.login(superuser)
    return admin_ui.edit(feed)


@pytest.fixture
def saved_product(admin_ui, superuser):
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


def test_an_accepted_save_leads_to_a_page_that_says_so(saved_product):
    assert saved_product.page.messages == [("success", ADDED)]


def test_a_message_has_its_level_and_its_text(saved_product):
    message = saved_product.page.messages[0]

    assert message.level == "success"
    assert message.text == ADDED


def test_a_message_equals_its_pair_written_either_way_but_not_its_text(saved_product):
    message = saved_product.page.messages[0]

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


def test_several_messages_of_several_levels_read_in_the_order_shown(adding_feed):
    """The warnings carry extra tags, which the admin draws as classes next to the level
    and which are no part of it."""
    adding_feed.populate(source="new feed.txt")

    result = adding_feed.save()

    items = result.page.native.locator("ul.messagelist > li").all()
    assert [item.get_attribute("class") for item in items] == [
        "source warning",
        "info warning",
        "success",
    ]
    assert result.page.messages == [
        ("warning", NOT_CSV),
        ("warning", SPACES),
        ("success", "The feed “new feed.txt” was added successfully."),
    ]


def test_an_extra_tag_that_names_a_level_does_not_change_the_level(adding_feed):
    """The admin draws the level after the extra tags, so the last level named wins."""
    adding_feed.populate(source="new feed.csv")

    result = adding_feed.save()

    item = result.page.native.locator("ul.messagelist > li").first
    assert item.get_attribute("class") == "info warning"
    assert result.page.messages[0] == ("warning", SPACES)


def test_a_level_without_a_tag_reads_as_no_level(refreshing_feed):
    """The history page "Refresh" leads to is a page the package does not model."""
    result = refreshing_feed.submit("_refresh")

    assert result.page.messages == [("", "The feed was refreshed.")]


def test_a_level_the_project_adds_reads_by_its_tag(message_tags, refreshing_feed):
    message_tags({35: "notice"})

    result = refreshing_feed.submit("_refresh")

    assert result.page.messages == [("notice", "The feed was refreshed.")]


def test_a_level_the_project_renames_reads_by_its_new_tag(message_tags, adding_feed):
    message_tags({30: "caution"})
    adding_feed.populate(source="catalogue.txt")

    result = adding_feed.save()

    assert result.page.messages[0] == ("caution", NOT_CSV)
