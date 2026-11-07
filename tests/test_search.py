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


def test_the_page_reads_the_results_of_a_search(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    assert page.search("Bolt") is None

    assert page.works
    assert not page.redirected
    assert page.status_code == 200
    assert page.destination == admin_ui.url.list(Product)
    assert page.count == 1
    assert page.summary == "1 product"
    assert not page.empty
    assert [row["name"].value for row in page.rows] == ["Bolt"]
    assert page.contains({"name": "Bolt"})


def test_several_results_are_reported_in_the_plural(admin_ui, superuser, products):
    """The term is in the name or the SKU of two of the three products."""
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    page.search("t")

    assert page.count == 2
    assert page.summary == "2 products"
    assert {row["name"].value for row in page.rows} == {"Bolt", "Nut"}


def test_a_search_that_finds_nothing_leaves_an_empty_changelist(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    page.search("no such product")

    assert page.works
    assert page.empty
    assert page.count == 0
    assert page.summary == "0 products"
    assert page.rows == []
    assert page.can_search


def test_the_same_search_can_be_run_again(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    page.search("Bolt")
    page.search("Bolt")

    assert page.count == 1


def test_one_page_can_search_several_times_in_a_row(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    page.search("Bolt")
    assert [row["name"].value for row in page.rows] == ["Bolt"]

    page.search("Washer")
    assert [row["name"].value for row in page.rows] == ["Washer"]


def test_an_empty_term_clears_the_search(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    page.search("Bolt")

    page.search("")

    assert page.count == 3


def test_a_search_keeps_the_filters_applied(admin_ui, superuser, products):
    """Two products named Bolt, of which the filter lets only the active one through."""
    Product.objects.create(name="Bolt", sku="SKU-Inactive", price="10.00", is_active=False)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    page.native.goto(admin_ui.absolute(f"{admin_ui.url.list(Product)}?is_active__exact=1"))

    page.search("Bolt")

    assert page.count == 1
    assert page.rows[0]["sku"].value == "SKU-Bolt"


def test_a_changelist_without_search_fields_refuses_a_search(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.list(Feed)
    before = page.native.url

    with pytest.raises(LookupError, match="The page offers no search"):
        page.search("anything")

    assert page.native.url == before


def test_a_search_after_the_session_ended_reports_the_refusal(admin_ui, superuser, products):
    """The admin sends the browser to the login page, and the page stands for where it landed."""
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    admin_ui.logout()

    page.search("Bolt")

    assert page.denied
    assert page.redirected
    assert not page.works
    assert page.destination == admin_ui.url.login()
    with pytest.raises(LookupError, match="The page did not open"):
        _ = page.rows


def test_the_term_is_empty_before_any_search(admin_ui, superuser):
    admin_ui.login(superuser)

    assert admin_ui.list(Product).search_term == ""


def test_the_term_is_empty_without_a_search_box(admin_ui, superuser):
    admin_ui.login(superuser)

    assert admin_ui.list(Feed).search_term == ""


def test_the_page_shows_the_term_it_searched_for(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    page.search("Bolt")

    assert page.search_term == "Bolt"


def test_the_term_keeps_its_spaces(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    page.search("  Bolt ")

    assert page.search_term == "  Bolt "
    assert page.count == 1


def test_the_term_is_empty_after_clearing_the_search(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    page.search("Bolt")

    page.search("")

    assert page.search_term == ""


def test_the_term_is_what_the_box_shows_now(admin_ui, superuser, products):
    """Text typed but not yet submitted is on the screen, so it reads as typed, while the rows
    still show the last search."""
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    page.search("Bolt")

    page.native.locator("#searchbar").fill("Nut")

    assert page.search_term == "Nut"
    assert [row["name"].value for row in page.rows] == ["Bolt"]


def test_a_page_that_did_not_open_cannot_show_a_term(admin_ui, adder):
    admin_ui.login(adder)
    page = admin_ui.list(Product)

    with pytest.raises(LookupError, match="The page did not open"):
        _ = page.search_term


def test_a_changelist_can_open_with_a_term_applied(admin_ui, superuser, products):
    admin_ui.login(superuser)

    page = admin_ui.list(Product, search="Bolt")

    assert page.works
    assert not page.redirected
    assert page.destination == admin_ui.url.list(Product)
    assert page.search_term == "Bolt"
    assert page.count == 1
    assert [row["name"].value for row in page.rows] == ["Bolt"]


def test_a_term_opened_with_reads_back_as_written(admin_ui, superuser, products):
    """Each of these characters means something else in a URL unless it is encoded."""
    admin_ui.login(superuser)
    term = "a&b=c #d+e"

    page = admin_ui.list(Product, search=term)

    assert page.search_term == term
    assert page.empty


def test_opening_with_an_empty_term_shows_every_record(admin_ui, superuser, products):
    admin_ui.login(superuser)

    page = admin_ui.list(Product, search="")

    assert page.works
    assert page.search_term == ""
    assert page.count == 3


def test_opening_with_a_term_refuses_a_changelist_without_search_fields(admin_ui, superuser):
    admin_ui.login(superuser)

    with pytest.raises(LookupError, match="The page offers no search"):
        admin_ui.list(Feed, search="anything")


def test_a_refused_user_opening_with_a_term_gets_a_denied_page(admin_ui, adder):
    admin_ui.login(adder)

    page = admin_ui.list(Product, search="Bolt")

    assert page.denied
    assert not page.works


def test_a_page_opened_with_a_term_can_search_again(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product, search="Bolt")

    page.search("Washer")

    assert page.search_term == "Washer"
    assert [row["name"].value for row in page.rows] == ["Washer"]
