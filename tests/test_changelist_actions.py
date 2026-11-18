"""The actions a changelist offers in its action bar, by name, the rows they run on, and running
them."""

import pytest
from django.contrib.auth.models import Permission
from django.contrib.sessions.models import Session

from django_admin_kit.actions import ChangelistAction
from django_admin_kit.pages import EditPage, LoginPage
from django_admin_kit.rows import NO_ACTIONS
from helpers import collect_page_loads, count_page_loads
from project.shop.admin import CategoryAdmin, ProductAdmin
from project.shop.models import Category, Product

# Django's warning when an action is run with no row selected.
NOTHING_SELECTED = (
    "Items must be selected in order to perform actions on them. No items have been changed."
)

# What the superuser is offered on the product changelist, by name and by label.
PRODUCT_ACTIONS = {
    "delete_selected": "Delete selected products",
    "mark_inactive": "Mark selected products as inactive",
    "open_first": "Open the first selected product",
}


def selection(page):
    """Whether each row on the page is selected, in order."""
    return [row.selected for row in page.rows]


def stored_is_active(*products):
    """Whether each of ``products`` is active, as stored now."""
    return [Product.objects.get(pk=product.pk).is_active for product in products]


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


def test_the_rows_start_unselected(admin_ui, superuser, products):
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert selection(page) == [False, False, False]


def test_a_row_is_selected_and_deselected_without_a_page_load(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    row = page.rows[1]

    assert count_page_loads(page, row.select) == 0
    assert selection(page) == [False, True, False]
    assert count_page_loads(page, row.deselect) == 0
    assert selection(page) == [False, False, False]


def test_selecting_a_selected_row_changes_nothing(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    page.rows[0].select()
    page.rows[0].select()

    assert selection(page) == [True, False, False]


def test_deselecting_a_row_that_isnt_selected_changes_nothing(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    page.rows[0].select()

    page.rows[2].deselect()

    assert selection(page) == [True, False, False]


def test_every_row_is_selected_at_once_without_a_page_load(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    page.rows[1].select()

    assert count_page_loads(page, page.select_all) == 0
    assert selection(page) == [True, True, True]


def test_selecting_every_row_when_each_is_selected_changes_nothing(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    for row in page.rows:
        row.select()

    page.select_all()

    assert selection(page) == [True, True, True]


def test_every_row_is_deselected_at_once_without_a_page_load(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    page.rows[0].select()
    page.rows[2].select()

    assert count_page_loads(page, page.deselect_all) == 0
    assert selection(page) == [False, False, False]


def test_deselecting_every_row_after_selecting_all_deselects_them(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    page.select_all()

    page.deselect_all()

    assert selection(page) == [False, False, False]


def test_deselecting_every_row_when_none_is_selected_changes_nothing(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    page.deselect_all()

    assert selection(page) == [False, False, False]


def test_rows_offered_no_actions_read_unselected_and_cannot_be_selected(admin_ui, viewer, products):
    admin_ui.login(viewer)
    page = admin_ui.list(Product)
    row = page.rows[0]

    assert selection(page) == [False, False, False]
    for select in (row.select, row.deselect, page.select_all, page.deselect_all):
        with pytest.raises(LookupError) as failure:
            select()
        assert str(failure.value) == NO_ACTIONS


def test_a_row_held_after_the_browser_left_cannot_be_selected(
    admin_ui, left_for, superuser, products
):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    row = page.rows[0]

    page.native.goto(admin_ui.absolute(admin_ui.url.index()))

    for read in (lambda: row.selected, row.select, row.deselect):
        with pytest.raises(LookupError) as failure:
            read()
        assert str(failure.value) == left_for(admin_ui.url.index())


def test_an_action_runs_on_the_selected_rows_and_comes_back_to_the_same_page(
    admin_ui, superuser, products
):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    page.rows[0].select()
    page.rows[2].select()

    landed = page.actions["mark_inactive"].run()

    assert landed is page
    assert page.messages == [("success", "2 products were marked as inactive.")]
    assert stored_is_active(*products) == [False, True, False]
    assert selection(page) == [False, False, False]


def test_an_action_keeps_the_search_and_the_filters(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    page.filters["is_active"].apply("Yes")
    page.search("Bolt")
    page.rows[0].select()

    landed = page.actions["mark_inactive"].run()

    assert landed is page
    assert page.search_term == "Bolt"
    assert page.filters["is_active"].selected == "Yes"
    assert stored_is_active(*products) == [False, True, True]


def test_an_action_run_with_nothing_selected_brings_back_djangos_warning(
    admin_ui, superuser, products
):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    landed = page.actions["mark_inactive"].run()

    assert landed is page
    assert page.messages == [("warning", NOTHING_SELECTED)]
    assert stored_is_active(*products) == [True, True, True]


def test_an_action_that_leads_elsewhere_returns_the_page_it_leads_to(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    page.rows[1].select()
    page.rows[2].select()

    landed = page.actions["open_first"].run()

    assert isinstance(landed, EditPage)
    assert landed.destination == admin_ui.url.edit(products[1])
    assert landed.works


def test_an_action_the_page_no_longer_offers_is_not_run(admin_ui, editor, products):
    """The editor loses the permission the action needs, and the page loads again."""
    admin_ui.login(editor)
    page = admin_ui.list(Product)
    action = page.actions["mark_inactive"]
    editor.user_permissions.remove(Permission.objects.get(codename="change_product"))
    page.search("Bolt")
    loads = collect_page_loads(page)

    with pytest.raises(LookupError) as failure:
        action.run()

    assert str(failure.value) == "The changelist no longer offers the action 'mark_inactive'."
    assert loads == []


def test_with_two_action_bars_the_action_runs_once_from_the_first(
    admin_ui, monkeypatch, superuser, products
):
    """Django runs what the bar of the button clicked chooses, and the second bar chooses
    nothing, so the action ran from the first."""
    monkeypatch.setattr(ProductAdmin, "actions_on_top", True)
    monkeypatch.setattr(ProductAdmin, "actions_on_bottom", True)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    page.rows[0].select()

    assert count_page_loads(page, page.actions["mark_inactive"].run) == 1
    assert page.messages == [("success", "1 products were marked as inactive.")]
    assert stored_is_active(*products) == [False, True, True]


def test_an_action_run_after_the_session_ended_reports_the_refusal(admin_ui, superuser, products):
    """The browser keeps its cookies, but the session behind them is gone."""
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    page.rows[0].select()
    Session.objects.all().delete()

    landed = page.actions["mark_inactive"].run()

    assert isinstance(landed, LoginPage)
    assert landed.denied
    assert landed.destination == admin_ui.url.login()
    assert stored_is_active(*products) == [True, True, True]
