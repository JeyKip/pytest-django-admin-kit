"""Submitting a create or edit page: whether the admin accepted it, where it sent the user,
and the page the browser shows afterwards."""

import datetime

import pytest

from django_admin_kit.pages import AdminPage, ChangelistPage, CreatePage, IndexPage
from project.shop.models import Product

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


@pytest.fixture
def saved(admin_ui, superuser):
    """A create page with a valid product, already saved."""
    admin_ui.login(superuser)
    page = admin_ui.create(Product)
    page.populate(WIDGET)
    return page.save()


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
