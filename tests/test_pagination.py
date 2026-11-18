"""Reading the pages of a changelist from the paginator the admin draws."""

import pytest

from django_admin_kit.pages import _with_page
from helpers import count_page_loads
from project.shop.admin import ProductAdmin
from project.shop.models import Product

# The address of the changelist the page links resolve against.
CHANGELIST = "http://localhost:8000/admin/shop/product/"


@pytest.fixture
def per_page(monkeypatch):
    """Sets how many products the changelist shows on a page, for one test."""
    return lambda count: monkeypatch.setattr(ProductAdmin, "list_per_page", count)


@pytest.fixture
def max_show_all(monkeypatch):
    """Sets how many products "Show all" may show at most, for one test."""
    return lambda count: monkeypatch.setattr(ProductAdmin, "list_max_show_all", count)


@pytest.fixture
def many_products(db):
    """Creates ``count`` products, named so the changelist lists them in the order created."""
    return lambda count: [
        Product.objects.create(name=f"Product {number:02}", sku=f"SKU-{number}", price="1.00")
        for number in range(1, count + 1)
    ]


def at_page(page, number):
    """Takes the browser to page ``number`` of the changelist, as its link would."""
    page.native.goto(f"{page.native.url.split('?')[0]}?p={number}")


def names(page):
    """The names of the products on the page shown, in order."""
    return [row["name"].value for row in page.rows]


def test_a_changelist_on_one_page_is_page_1_of_1(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    assert page.page_number == 1
    assert page.page_count == 1


def test_an_empty_changelist_is_page_1_of_1(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    assert page.empty
    assert page.page_number == 1
    assert page.page_count == 1


def test_a_changelist_opens_on_its_first_page(admin_ui, superuser, per_page, many_products):
    per_page(2)
    many_products(5)
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert page.page_number == 1
    assert page.page_count == 3


@pytest.mark.parametrize("number", [2, 3])
def test_the_page_shown_is_the_one_the_paginator_marks(
    admin_ui, superuser, per_page, many_products, number
):
    """The last page has no link of its own, so its number is read from the mark alone."""
    per_page(2)
    many_products(5)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    at_page(page, number)

    assert page.page_number == number
    assert page.page_count == 3


@pytest.mark.parametrize("number", [1, 10, 20])
def test_the_count_includes_the_pages_the_paginator_leaves_out(
    admin_ui, superuser, per_page, many_products, number
):
    """Django shows the first two pages, the last two and three on each side of the current
    one, with an ellipsis for the rest."""
    per_page(1)
    many_products(20)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    at_page(page, number)

    assert "…" in page.native.locator(".paginator").inner_text()
    assert page.page_number == number
    assert page.page_count == 20


def test_the_rows_are_those_of_the_page_shown(admin_ui, superuser, per_page, many_products):
    per_page(2)
    many_products(5)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    at_page(page, 3)

    assert page.count == 5
    assert [row["name"].value for row in page.rows] == ["Product 05"]


def test_a_page_that_did_not_open_has_no_pages_to_read(admin_ui, adder):
    admin_ui.login(adder)
    page = admin_ui.list(Product)

    with pytest.raises(LookupError, match="The page did not open"):
        _ = page.page_number
    with pytest.raises(LookupError, match="The page did not open"):
        _ = page.page_count


@pytest.mark.parametrize(("start", "number"), [(1, 2), (1, 3), (3, 1), (2, 3)])
def test_going_to_a_page_with_a_link_clicks_it(
    admin_ui, superuser, per_page, many_products, start, number
):
    per_page(2)
    many_products(5)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    at_page(page, start)

    assert count_page_loads(page, lambda: page.go_to_page(number)) == 1

    assert page.works
    assert page.destination == admin_ui.url.list(Product)
    assert page.page_number == number
    assert page.page_count == 3


@pytest.mark.parametrize(("start", "number"), [(1, 10), (20, 5), (10, 4), (10, 16)])
def test_going_to_a_page_without_a_link_opens_it_in_one_load(
    admin_ui, superuser, per_page, many_products, start, number
):
    """From page 1 of 20 the paginator shows 1 2 3 4 … 19 20, from page 20 it shows 1 2 … 17 18
    19 20, and from page 10 it shows 1 2 … 7 to 13 … 19 20, so none of these pages has a link."""
    per_page(1)
    many_products(20)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    at_page(page, start)

    assert count_page_loads(page, lambda: page.go_to_page(number)) == 1

    assert page.works
    assert page.page_number == number
    assert page.page_count == 20
    assert names(page) == [f"Product {number:02}"]


def test_the_rows_are_those_of_the_page_gone_to(admin_ui, superuser, per_page, many_products):
    per_page(2)
    many_products(5)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    page.go_to_page(2)

    assert names(page) == ["Product 03", "Product 04"]
    assert page.count == 5


def test_going_to_the_page_shown_loads_nothing(admin_ui, superuser, per_page, many_products):
    per_page(2)
    many_products(5)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    assert count_page_loads(page, lambda: page.go_to_page(1)) == 0

    assert page.page_number == 1


@pytest.mark.parametrize("number", [2, 10])
def test_the_search_filters_and_sort_stay_applied_on_another_page(
    admin_ui, superuser, per_page, many_products, number
):
    """Page 2 has a link from page 1, and page 10 has none."""
    per_page(1)
    many_products(20)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    page.search("Product")
    page.filters["is_active"].apply("Yes")
    page.sort("-name")

    page.go_to_page(number)

    assert page.page_number == number
    assert page.search_term == "Product"
    assert page.filters["is_active"].selected == "Yes"
    assert page.sorted_columns == ["-name"]
    assert names(page) == [f"Product {21 - number:02}"]


@pytest.mark.parametrize(
    "change",
    [
        lambda page: page.search("Product"),
        lambda page: page.filters["is_active"].apply("Yes"),
        lambda page: page.sort("-name"),
    ],
    ids=["search", "filter", "sort"],
)
def test_a_search_a_filter_or_a_sort_goes_back_to_the_first_page(
    admin_ui, superuser, per_page, many_products, change
):
    """Django's links for them leave out the page number."""
    per_page(2)
    many_products(5)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    page.go_to_page(3)

    change(page)

    assert page.page_number == 1
    assert page.page_count == 3


@pytest.mark.parametrize(
    ("number", "error", "message"),
    [
        (0, LookupError, "The changelist has 3 pages, so there is no page 0."),
        (-1, LookupError, "The changelist has 3 pages, so there is no page -1."),
        (4, LookupError, "The changelist has 3 pages, so there is no page 4."),
        (True, TypeError, "A page number is an int, not bool."),
        ("2", TypeError, "A page number is an int, not str."),
        (None, TypeError, "A page number is an int, not NoneType."),
        (2.0, TypeError, "A page number is an int, not float."),
    ],
)
def test_a_page_number_that_is_not_a_page_is_refused_before_anything_is_clicked(
    admin_ui, superuser, per_page, many_products, number, error, message
):
    per_page(2)
    many_products(5)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    def go():
        with pytest.raises(error) as raised:
            page.go_to_page(number)
        assert str(raised.value) == message

    assert count_page_loads(page, go) == 0

    assert page.page_number == 1


def test_a_changelist_of_one_page_has_no_other_page(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    with pytest.raises(LookupError) as raised:
        page.go_to_page(2)

    assert str(raised.value) == "The changelist has 1 page, so there is no page 2."


@pytest.mark.parametrize("number", [2, 10])
def test_going_to_a_page_after_the_session_ended_reports_the_refusal(
    admin_ui, superuser, per_page, many_products, number
):
    """Page 2 has a link from page 1, and page 10 has none."""
    per_page(1)
    many_products(20)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    admin_ui.logout()

    page.go_to_page(number)

    assert page.denied
    assert page.redirected
    assert page.destination == admin_ui.url.login()
    with pytest.raises(LookupError, match="The page did not open"):
        _ = page.page_number


def test_a_page_that_did_not_open_cannot_go_to_another_page(admin_ui, adder):
    admin_ui.login(adder)
    page = admin_ui.list(Product)

    with pytest.raises(LookupError, match="The page did not open"):
        page.go_to_page(2)


@pytest.mark.parametrize(
    ("href", "address"),
    [
        ("?p=2", f"{CHANGELIST}?p=5"),
        ("?o=-1&p=2&q=bolt", f"{CHANGELIST}?o=-1&q=bolt&p=5"),
        ("?q=bolt", f"{CHANGELIST}?q=bolt&p=5"),
        ("?all=&p=2", f"{CHANGELIST}?all=&p=5"),
        ("?id__in=1&id__in=2&p=2", f"{CHANGELIST}?id__in=1&id__in=2&p=5"),
        ("?q=two+words&p=2", f"{CHANGELIST}?q=two+words&p=5"),
    ],
    ids=["page-only", "others-kept-in-order", "page-added", "blank-value", "repeated", "encoded"],
)
def test_the_address_of_a_page_without_a_link_is_a_drawn_link_with_its_number_changed(
    href, address
):
    assert _with_page(f"{CHANGELIST}?p=1", href, 5) == address


def test_a_changelist_of_several_pages_offers_to_show_all(
    admin_ui, superuser, per_page, many_products
):
    per_page(2)
    many_products(5)
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert page.can_show_all is True
    assert page.shows_all is False


def test_a_changelist_of_one_page_offers_no_show_all(admin_ui, superuser, products):
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert page.can_show_all is False
    assert page.shows_all is False


def test_too_many_records_to_show_at_once_offer_no_show_all(
    admin_ui, superuser, per_page, max_show_all, many_products
):
    per_page(2)
    max_show_all(4)
    many_products(5)
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert page.can_show_all is False
    assert page.page_count == 3


def test_showing_all_puts_every_record_on_one_page(admin_ui, superuser, per_page, many_products):
    per_page(2)
    many_products(5)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    assert count_page_loads(page, page.show_all) == 1

    assert page.works
    assert page.destination == admin_ui.url.list(Product)
    assert page.shows_all is True
    assert page.can_show_all is False
    assert page.page_number == 1
    assert page.page_count == 1
    assert page.count == 5
    assert names(page) == [f"Product {number:02}" for number in range(1, 6)]


def test_showing_all_from_another_page_shows_them_all_too(
    admin_ui, superuser, per_page, many_products
):
    per_page(2)
    many_products(5)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    page.go_to_page(3)

    page.show_all()

    assert page.shows_all
    assert len(page.rows) == 5


def test_showing_all_again_loads_nothing(admin_ui, superuser, per_page, many_products):
    per_page(2)
    many_products(5)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    page.show_all()

    assert count_page_loads(page, page.show_all) == 0

    assert page.shows_all


def test_a_changelist_of_one_page_reads_as_showing_all_once_asked(admin_ui, superuser, products):
    """The address asks for all records, and they are all on the page."""
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    page.native.goto(f"{page.native.url}?all=")

    assert page.shows_all is True


def test_asking_for_all_of_too_many_records_does_not_show_all(
    admin_ui, superuser, per_page, max_show_all, many_products
):
    """Django ignores the request and shows the pages."""
    per_page(2)
    max_show_all(4)
    many_products(5)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    page.native.goto(f"{page.native.url}?all=")

    assert page.shows_all is False
    assert page.page_count == 3


@pytest.mark.parametrize("fits", [True, False], ids=["one-page", "too-many"])
def test_a_changelist_that_cannot_show_all_refuses_before_anything_is_clicked(
    admin_ui, superuser, per_page, max_show_all, many_products, fits
):
    if not fits:
        per_page(2)
        max_show_all(4)
    many_products(5)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    def show():
        with pytest.raises(LookupError) as raised:
            page.show_all()
        assert str(raised.value) == "The changelist doesn't offer to show all of its records."

    assert count_page_loads(page, show) == 0


@pytest.mark.parametrize(
    "change",
    [
        lambda page: page.search("Product"),
        lambda page: page.filters["is_active"].apply("Yes"),
        lambda page: page.sort("-name"),
    ],
    ids=["search", "filter", "sort"],
)
def test_a_search_a_filter_or_a_sort_keeps_showing_all(
    admin_ui, superuser, per_page, many_products, change
):
    per_page(2)
    many_products(5)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    page.show_all()

    change(page)

    assert page.shows_all
    assert len(page.rows) == 5


def test_no_page_but_the_first_can_be_gone_to_while_showing_all(
    admin_ui, superuser, per_page, many_products
):
    per_page(2)
    many_products(5)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    page.show_all()

    with pytest.raises(LookupError) as raised:
        page.go_to_page(2)

    assert str(raised.value) == (
        "The changelist shows all of its records on one page, so there is no page 2."
    )
    assert count_page_loads(page, lambda: page.go_to_page(1)) == 0


def test_showing_all_after_the_session_ended_reports_the_refusal(
    admin_ui, superuser, per_page, many_products
):
    per_page(2)
    many_products(5)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    admin_ui.logout()

    page.show_all()

    assert page.denied
    assert page.redirected
    assert page.destination == admin_ui.url.login()
    with pytest.raises(LookupError, match="The page did not open"):
        _ = page.shows_all


def test_a_page_that_did_not_open_cannot_show_all(admin_ui, adder):
    admin_ui.login(adder)
    page = admin_ui.list(Product)

    with pytest.raises(LookupError, match="The page did not open"):
        _ = page.can_show_all
    with pytest.raises(LookupError, match="The page did not open"):
        _ = page.shows_all
    with pytest.raises(LookupError, match="The page did not open"):
        page.show_all()
