"""Which actions a create or edit page offers, and whether it links to deleting its object.

The admin decides both from the user's permissions and the admin's own settings, so each
case names the user and the page it opens.
"""

import pytest

from django_admin_kit.pages import FormAction
from project.shop.models import Feed, Product

SAVE = FormAction.SAVE
CONTINUE = FormAction.SAVE_AND_CONTINUE
ADD_ANOTHER = FormAction.SAVE_AND_ADD_ANOTHER
SAVE_AS_NEW = FormAction.SAVE_AS_NEW

# How each case opens its page, given the session and the fixtures by name.
PAGES = {
    "product's edit page": lambda admin_ui, get: admin_ui.edit(get("product")),
    "product's create page": lambda admin_ui, get: admin_ui.create(Product),
    "released product's edit page": lambda admin_ui, get: admin_ui.edit(get("released")),
    "feed's edit page": lambda admin_ui, get: admin_ui.edit(get("feed")),
    "feed's create page": lambda admin_ui, get: admin_ui.create(Feed),
}


def opened(admin_ui, request, user, page):
    admin_ui.login(request.getfixturevalue(user))
    return PAGES[page](admin_ui, request.getfixturevalue)


@pytest.mark.parametrize(
    ("user", "page", "offered"),
    [
        ("superuser", "product's edit page", {SAVE, CONTINUE, ADD_ANOTHER}),
        ("superuser", "product's create page", {SAVE, CONTINUE, ADD_ANOTHER}),
        ("superuser", "released product's edit page", {SAVE, CONTINUE, ADD_ANOTHER}),
        ("editor", "product's edit page", {SAVE, CONTINUE}),
        # Continuing would open the object's page, which the adder may not view.
        ("adder", "product's create page", {SAVE, ADD_ANOTHER}),
        ("viewer", "product's edit page", set()),
        ("superuser", "feed's edit page", {SAVE, CONTINUE, SAVE_AS_NEW, "_refresh"}),
        ("superuser", "feed's create page", {SAVE, CONTINUE, ADD_ANOTHER}),
    ],
)
def test_a_form_offers_the_actions_the_admin_gives_its_user(admin_ui, request, user, page, offered):
    assert opened(admin_ui, request, user, page).actions == offered


@pytest.mark.parametrize(
    ("user", "page", "deletable"),
    [
        ("superuser", "product's edit page", True),
        ("superuser", "product's create page", False),
        # The shop's rule: a released product stays on record.
        ("superuser", "released product's edit page", False),
        ("editor", "product's edit page", False),
        ("viewer", "product's edit page", False),
        ("superuser", "feed's edit page", True),
    ],
)
def test_a_form_links_to_deleting_its_object_where_the_admin_allows_it(
    admin_ui, request, user, page, deletable
):
    assert opened(admin_ui, request, user, page).can_delete is deletable


def test_the_actions_are_the_names_the_buttons_post(admin_ui, superuser, product):
    admin_ui.login(superuser)

    page = admin_ui.edit(product)

    assert page.actions == {"_save", "_continue", "_addanother"}


def test_an_action_is_looked_up_by_constant_or_by_name(admin_ui, editor, product):
    admin_ui.login(editor)

    page = admin_ui.edit(product)

    assert page.has_action(FormAction.SAVE)
    assert page.has_action("_continue")
    assert not page.has_action(FormAction.SAVE_AND_ADD_ANOTHER)
    assert not page.has_action("_approve")


def test_each_admin_action_has_its_own_check(admin_ui, editor, product):
    admin_ui.login(editor)

    page = admin_ui.edit(product)

    assert page.can_save
    assert page.can_save_and_continue
    assert not page.can_save_and_add_another
    assert not page.can_save_as_new
    assert not page.can_delete


def test_an_admin_that_copies_records_offers_save_as_new_in_its_checks(admin_ui, superuser, feed):
    admin_ui.login(superuser)

    page = admin_ui.edit(feed)

    assert page.can_save
    assert page.can_save_and_continue
    assert not page.can_save_and_add_another
    assert page.can_save_as_new
    assert page.can_delete


def test_a_refused_page_has_no_actions_to_read(admin_ui, adder, product):
    admin_ui.login(adder)

    page = admin_ui.edit(product)

    with pytest.raises(LookupError) as failure:
        set(page.actions)

    assert str(failure.value) == (
        "The page did not open, so there is nothing to read from it. "
        f"Status 403, at {admin_ui.url.edit(product)}."
    )


def test_a_refused_page_has_no_delete_link_to_read(admin_ui, adder, product):
    admin_ui.login(adder)

    page = admin_ui.edit(product)

    with pytest.raises(LookupError) as failure:
        bool(page.can_delete)

    assert str(failure.value) == (
        "The page did not open, so there is nothing to read from it. "
        f"Status 403, at {admin_ui.url.edit(product)}."
    )
