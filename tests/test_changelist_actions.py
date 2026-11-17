"""The actions a changelist offers in its action bar, by name."""

import pytest
from django.contrib.auth.models import Permission

from django_admin_kit.actions import ChangelistAction
from project.shop.admin import CategoryAdmin, ProductAdmin
from project.shop.models import Category, Product

# What the superuser is offered on the product changelist, by name and by label.
PRODUCT_ACTIONS = {
    "delete_selected": "Delete selected products",
    "mark_inactive": "Mark selected products as inactive",
    "open_first": "Open the first selected product",
}


def test_the_actions_are_listed_by_name_in_the_order_the_bar_lists_them(
    admin_ui, superuser, products
):
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert list(page.actions) == list(PRODUCT_ACTIONS)


def test_each_action_reads_its_name_and_its_label(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    actions = {name: page.actions[name] for name in page.actions}

    assert all(isinstance(action, ChangelistAction) for action in actions.values())
    assert {name: action.name for name, action in actions.items()} == {
        name: name for name in PRODUCT_ACTIONS
    }
    assert {name: action.label for name, action in actions.items()} == PRODUCT_ACTIONS


def test_an_action_has_its_option_as_native(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    option = page.actions["mark_inactive"].native

    assert option.evaluate("option => option.tagName") == "OPTION"
    assert option.get_attribute("value") == "mark_inactive"


def test_the_actions_read_as_a_mapping(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    assert len(page.actions) == 3
    assert "mark_inactive" in page.actions
    assert "archive" not in page.actions
    assert [action.label for action in page.actions.values()] == list(PRODUCT_ACTIONS.values())


def test_a_user_who_may_not_delete_is_offered_the_admins_own_actions(admin_ui, editor, products):
    admin_ui.login(editor)

    page = admin_ui.list(Product)

    assert list(page.actions) == ["mark_inactive", "open_first"]


def test_a_user_who_may_only_view_is_offered_no_actions(admin_ui, viewer, products):
    admin_ui.login(viewer)
    page = admin_ui.list(Product)

    assert list(page.actions) == []
    assert not page.actions
    with pytest.raises(KeyError) as failure:
        _ = page.actions["delete_selected"]

    assert failure.value.args[0] == (
        "No action named 'delete_selected' here. The changelist offers no actions."
    )


def test_an_admin_without_actions_offers_none(admin_ui, monkeypatch, superuser, category):
    monkeypatch.setattr(CategoryAdmin, "actions", None)
    admin_ui.login(superuser)

    page = admin_ui.list(Category)

    assert list(page.actions) == []


def test_a_model_without_records_offers_no_actions(admin_ui, superuser, db):
    """Django draws no action bar while it counts the records and finds none."""
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert list(page.actions) == []


@pytest.mark.parametrize(
    "key",
    ["archive", "Mark selected products as inactive", ""],
    ids=["an unknown name", "a label", "the blank option"],
)
def test_a_key_that_names_no_action_is_a_miss_that_lists_the_names(
    admin_ui, superuser, products, key
):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    with pytest.raises(KeyError) as failure:
        _ = page.actions[key]

    assert failure.value.args[0] == (
        f"No action named {key!r} here. Actions: 'delete_selected', 'mark_inactive', 'open_first'."
    )


def test_an_action_keeps_working_after_the_page_loads_again(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    action = page.actions["mark_inactive"]

    page.search("Bolt")

    assert action.label == "Mark selected products as inactive"


def test_an_action_the_page_no_longer_offers_raises(admin_ui, editor, products):
    """The editor loses the permission the action needs, and the page loads again."""
    admin_ui.login(editor)
    page = admin_ui.list(Product)
    action = page.actions["mark_inactive"]

    editor.user_permissions.remove(Permission.objects.get(codename="change_product"))
    page.search("Bolt")

    with pytest.raises(LookupError) as failure:
        _ = action.label

    assert str(failure.value) == "The changelist no longer offers the action 'mark_inactive'."


def test_two_action_bars_list_the_actions_once(admin_ui, monkeypatch, superuser, products):
    monkeypatch.setattr(ProductAdmin, "actions_on_top", True)
    monkeypatch.setattr(ProductAdmin, "actions_on_bottom", True)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    assert page.native.locator("div.actions").count() == 2
    assert list(page.actions) == list(PRODUCT_ACTIONS)
    assert page.actions["mark_inactive"].label == "Mark selected products as inactive"


def test_a_page_that_did_not_open_has_no_actions_to_read(admin_ui, adder):
    admin_ui.login(adder)
    page = admin_ui.list(Product)

    with pytest.raises(LookupError, match="The page did not open"):
        _ = page.actions
