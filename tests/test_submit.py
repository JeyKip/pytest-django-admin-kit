"""Submitting a create or edit page: whether the admin accepted it, where it sent the user,
and the page the browser shows afterwards."""

import datetime
from urllib.parse import urlsplit

import pytest
from django.urls import reverse

from django_admin_kit.pages import AdminPage, ChangelistPage, CreatePage, EditPage, IndexPage
from project.shop.models import Feed, Product

# A page without a form, standing in for a confirmation page that a project's
# `response_add` might render instead of redirecting.
INTERMEDIATE = "<html><body><div id='content'><h1>Are you sure?</h1></div></body></html>"

# Every field the product form requires, so the admin accepts the save.
WIDGET = {
    "name": "Widget",
    "sku": "SKU-1",
    "price": "10.00",
    "released_on": datetime.date(2026, 1, 15),
}


# Every way of reading a create or edit page, by what it reads.
PAGE_READERS = {
    "status_code": lambda page: page.status_code,
    "destination": lambda page: page.destination,
    "redirected": lambda page: page.redirected,
    "works": lambda page: page.works,
    "denied": lambda page: page.denied,
    "missing": lambda page: page.missing,
    "title": lambda page: page.title,
    "subtitle": lambda page: page.subtitle,
    "fields": lambda page: page.fields,
    "required_fields": lambda page: page.required_fields,
    "optional_fields": lambda page: page.optional_fields,
    "errors": lambda page: page.errors,
    "actions": lambda page: page.actions,
    "has_action": lambda page: page.has_action("_save"),
    "can_save": lambda page: page.can_save,
    "can_save_and_continue": lambda page: page.can_save_and_continue,
    "can_save_and_add_another": lambda page: page.can_save_and_add_another,
    "can_save_as_new": lambda page: page.can_save_as_new,
    "can_delete": lambda page: page.can_delete,
    "populate": lambda page: page.populate(name="Gadget"),
    "submit": lambda page: page.submit("_save"),
    "save": lambda page: page.save(),
}

# Every way of reading a field, by what it reads.
FIELD_READERS = {
    "value": lambda field: field.value,
    "links": lambda field: field.links,
    "required": lambda field: field.required,
    "label": lambda field: field.label,
    "editable": lambda field: field.editable,
    "choices": lambda field: field.choices,
    "fill": lambda field: field.fill("Gadget"),
}


@pytest.fixture
def filled(admin_ui, superuser):
    """A create page with a valid product, not yet saved."""
    admin_ui.login(superuser)
    page = admin_ui.create(Product)
    page.populate(WIDGET)
    return page


@pytest.fixture
def saved(filled):
    return filled.save()


@pytest.fixture
def incomplete(admin_ui, superuser):
    """A create page with only a name filled in, so the admin rejects it."""
    admin_ui.login(superuser)
    page = admin_ui.create(Product)
    page.populate(name="Widget")
    return page


@pytest.fixture
def rejected(incomplete):
    return incomplete.save()


@pytest.fixture
def refreshing(admin_ui, superuser, feed):
    """A feed's edit page with a new source filled in, ready for the project's own
    "Refresh" button."""
    admin_ui.login(superuser)
    page = admin_ui.edit(feed)
    page.populate(source="refreshed.csv")
    return page


@pytest.fixture
def renaming(admin_ui, superuser, released):
    """The released product's edit page with a new name filled in. The released product,
    because the form requires a release date."""
    admin_ui.login(superuser)
    page = admin_ui.edit(released)
    page.populate(name="Gadget")
    return page


def test_an_accepted_save_is_a_success_and_stores_the_object(saved):
    assert saved.success
    assert Product.objects.filter(sku="SKU-1").exists()


def test_an_accepted_save_is_redirected_to_the_changelist(admin_ui, saved):
    assert saved.redirected_to(admin_ui.url.list(Product))


def test_an_accepted_save_carries_the_changelist_it_led_to(saved):
    assert isinstance(saved.page, ChangelistPage)
    assert saved.page.works
    assert saved.page.count == 1


def test_an_edit_page_saves_a_new_value(admin_ui, superuser, released):
    """Uses the released product, because the form requires a release date."""
    admin_ui.login(superuser)
    page = admin_ui.edit(released)
    page.populate(name="Gadget")

    result = page.save()

    assert result.success
    released.refresh_from_db()
    assert released.name == "Gadget"


def test_a_rejected_save_is_no_success_and_stores_nothing(rejected):
    assert not rejected.success
    assert not Product.objects.exists()


def test_a_rejected_save_is_not_redirected_anywhere(admin_ui, rejected):
    """The rejected form is shown again at its own URL, but no redirect happened."""
    assert not rejected.redirected_to(admin_ui.url.list(Product))
    assert not rejected.redirected_to(admin_ui.url.create(Product))


def test_a_rejected_save_carries_the_submitted_page_itself(incomplete, rejected):
    assert rejected.page is incomplete
    assert isinstance(rejected.page, CreatePage)
    assert rejected.page.works


def test_a_rejected_form_comes_back_with_what_was_submitted(rejected):
    assert rejected.page.fields["name"].value == "Widget"
    assert rejected.page.fields["sku"].value == ""


def test_another_kind_of_page_at_the_same_address_is_a_plain_admin_page(admin_ui, incomplete):
    """The URL is the create page's, but the response is not a form, so the result's
    page is a plain AdminPage."""
    incomplete.native.route(
        admin_ui.absolute(admin_ui.url.create(Product)),
        lambda route: (
            route.fulfill(status=200, content_type="text/html", body=INTERMEDIATE)
            if route.request.method == "POST"
            else route.continue_()
        ),
    )

    result = incomplete.save()

    assert result.page is not incomplete
    assert type(result.page) is AdminPage
    assert result.page.works
    assert result.page.title == "Are you sure?"


def test_a_save_by_a_user_who_may_not_view_the_list_leads_to_the_index(admin_ui, adder):
    admin_ui.login(adder)
    page = admin_ui.create(Product)
    page.populate(WIDGET)

    result = page.save()

    assert result.success
    assert isinstance(result.page, IndexPage)
    assert result.page.works


def test_an_action_the_page_does_not_offer_submits_nothing(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Product)
    page.populate(WIDGET)

    with pytest.raises(LookupError) as failure:
        page.submit("_approve")

    assert str(failure.value) == (
        "The page offers no action '_approve'. Actions: '_addanother', '_continue', '_save'."
    )
    assert not Product.objects.exists()


def test_saving_a_page_that_offers_no_save_names_no_actions(admin_ui, viewer, product):
    admin_ui.login(viewer)
    page = admin_ui.edit(product)

    with pytest.raises(LookupError) as failure:
        page.save()

    assert str(failure.value) == "The page offers no action '_save'. Actions: none."


def test_continuing_on_an_edit_page_is_redirected_back_to_it(admin_ui, released, renaming):
    result = renaming.save_and_continue()

    assert result.success
    assert result.redirected_to(admin_ui.url.edit(released))


def test_continuing_on_an_edit_page_carries_the_same_page(renaming):
    result = renaming.save_and_continue()

    assert result.page is renaming
    assert renaming.fields["name"].value == "Gadget"


def test_continuing_on_a_create_page_leads_to_the_new_objects_edit_page(admin_ui, filled):
    result = filled.save_and_continue()

    widget = Product.objects.get(sku="SKU-1")
    assert result.redirected_to(admin_ui.url.edit(widget))
    assert isinstance(result.page, EditPage)
    assert result.page.works


def test_continuing_on_a_create_page_leaves_it(admin_ui, left_for, filled):
    filled.save_and_continue()

    with pytest.raises(LookupError) as failure:
        bool(filled.works)

    widget = Product.objects.get(sku="SKU-1")
    assert str(failure.value) == left_for(admin_ui.url.edit(widget))


def test_adding_another_is_redirected_back_to_the_create_page(admin_ui, filled):
    result = filled.save_and_add_another()

    assert result.success
    assert result.redirected_to(admin_ui.url.create(Product))
    assert Product.objects.filter(sku="SKU-1").exists()


def test_adding_another_carries_the_same_page_now_empty(filled):
    result = filled.save_and_add_another()

    assert result.page is filled
    assert filled.fields["name"].value == ""


def test_a_user_who_may_not_add_cannot_add_another(admin_ui, editor, product):
    admin_ui.login(editor)
    page = admin_ui.edit(product)

    with pytest.raises(LookupError) as failure:
        page.save_and_add_another()

    assert str(failure.value) == (
        "The page offers no action '_addanother'. Actions: '_continue', '_save'."
    )


def test_saving_as_new_stores_a_copy_and_leaves_the_original(admin_ui, superuser, feed):
    admin_ui.login(superuser)
    page = admin_ui.edit(feed)
    page.populate(source="copy.csv")

    result = page.save_as_new()

    copy = Feed.objects.exclude(pk=feed.pk).get()
    feed.refresh_from_db()
    assert result.success
    assert feed.source == "catalogue.csv"
    assert copy.source == "copy.csv"


def test_saving_as_new_is_redirected_to_the_copys_edit_page(admin_ui, superuser, feed):
    admin_ui.login(superuser)
    page = admin_ui.edit(feed)
    page.populate(source="copy.csv")

    result = page.save_as_new()

    copy = Feed.objects.exclude(pk=feed.pk).get()
    assert result.redirected_to(admin_ui.url.edit(copy))
    assert isinstance(result.page, EditPage)


def test_an_admin_that_does_not_copy_records_offers_no_save_as_new(admin_ui, superuser, product):
    admin_ui.login(superuser)
    page = admin_ui.edit(product)

    with pytest.raises(LookupError) as failure:
        page.save_as_new()

    assert str(failure.value) == (
        "The page offers no action '_saveasnew'. Actions: '_addanother', '_continue', '_save'."
    )


@pytest.mark.parametrize("read", PAGE_READERS.values(), ids=PAGE_READERS.keys())
def test_a_page_the_browser_left_fails_at_once_when_read(admin_ui, left_for, filled, read):
    filled.save()

    with pytest.raises(LookupError) as failure:
        read(filled)

    assert str(failure.value) == left_for(admin_ui.url.list(Product))


@pytest.mark.parametrize("read", FIELD_READERS.values(), ids=FIELD_READERS.keys())
def test_a_field_of_a_page_the_browser_left_fails_at_once_when_read(
    admin_ui, left_for, filled, read
):
    field = filled.fields["name"]
    filled.save()

    with pytest.raises(LookupError) as failure:
        read(field)

    assert str(failure.value) == left_for(admin_ui.url.list(Product))


def test_what_reads_nothing_from_a_page_the_browser_left_still_answers(admin_ui, filled):
    """The native handle is the browser layer's own object, and a field's name and repr
    come from the field itself."""
    field = filled.fields["name"]
    filled.save()

    assert urlsplit(filled.native.url).path == admin_ui.url.list(Product)
    assert field.name == "name"
    assert repr(field) == "FormField('name')"


def test_a_save_that_leads_to_the_changelist_is_redirected_to_the_list(saved):
    assert saved.redirected_to_list(Product)


def test_a_save_that_leads_to_the_index_is_redirected_to_the_index(admin_ui, adder):
    """The adder may not view the changelist, so the admin sends them to the index."""
    admin_ui.login(adder)
    page = admin_ui.create(Product)
    page.populate(WIDGET)

    result = page.save()

    assert result.redirected_to_index()


def test_adding_another_is_redirected_to_the_create_page(filled):
    assert filled.save_and_add_another().redirected_to_create(Product)


def test_continuing_is_redirected_to_the_edit_page(released, renaming):
    assert renaming.save_and_continue().redirected_to_edit(released)


def test_a_rejected_save_is_not_redirected_to_the_create_page_it_is_on(rejected):
    assert not rejected.redirected_to_create(Product)


def test_an_action_the_project_adds_saves_what_was_filled_in(feed, refreshing):
    result = refreshing.submit("_refresh")

    feed.refresh_from_db()
    assert result.success
    assert feed.source == "refreshed.csv"


def test_an_action_the_project_adds_goes_where_the_project_sends_it(feed, refreshing):
    """The project's code sends "Refresh" to the feed's history, where a plain save would
    go to the changelist."""
    result = refreshing.submit("_refresh")

    assert result.redirected_to(reverse("admin:shop_feed_history", args=[feed.pk]))


def test_a_page_the_package_does_not_model_is_a_plain_admin_page(refreshing):
    """The history page is the admin's, but the package has no page type for it."""
    result = refreshing.submit("_refresh")

    assert type(result.page) is AdminPage
    assert result.page.works
