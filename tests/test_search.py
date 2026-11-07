"""Searching a changelist through the search box the admin draws for it."""

import pytest

from project.shop.models import Feed, Product


def test_a_changelist_with_search_fields_offers_a_search(admin_ui, superuser):
    admin_ui.login(superuser)

    assert admin_ui.list(Product).can_search is True


def test_a_user_who_may_only_view_is_offered_the_search_too(admin_ui, viewer):
    admin_ui.login(viewer)

    assert admin_ui.list(Product).can_search is True


def test_a_changelist_without_search_fields_offers_no_search(admin_ui, superuser):
    admin_ui.login(superuser)

    assert admin_ui.list(Feed).can_search is False


def test_a_page_that_did_not_open_cannot_say_whether_it_offers_a_search(admin_ui, adder):
    admin_ui.login(adder)
    page = admin_ui.list(Product)

    with pytest.raises(LookupError, match="The page did not open"):
        _ = page.can_search
