"""A changelist's columns as objects, and sorting by them."""

import datetime

import django
import pytest

from django_admin_kit.columns import SortDirection
from project.shop.models import Feed, Product

# The product columns the user can sort by: the fields, and the method with an ordering.
SORTABLE = ["name", "sku", "price", "is_active", "featured", "released_on", "is_released"]
# What a product column is called on the page, by the name it is addressed by.
LABELS = {"price": "Price", "is_released": "Released", "price_with_tax": "Price with tax"}
# The product columns, as the error of an unknown name lists them.
COLUMN_LIST = (
    "'name', 'sku', 'price', 'is_active', 'featured', 'released_on', 'is_released', "
    "'price_with_tax', 'documents'"
)
# Price descending, then name, in Django's `o` parameter, which counts the columns from the
# action checkbox for a user who has actions and from the name for one who has none.
PRICE_THEN_NAME = {"superuser": "-3.1", "viewer": "-2.0"}
# The products by name, the way each sort orders them: by name descending, by price, by price
# descending, by release date, and by when they were added, newest first.
BY_NAME_DESCENDING = ["Washer", "Nut", "Bolt"]
BY_PRICE = ["Nut", "Washer", "Bolt"]
BY_PRICE_DESCENDING = ["Bolt", "Washer", "Nut"]
BY_RELEASE = ["Washer", "Nut", "Bolt"]
NEWEST_FIRST = ["Washer", "Nut", "Bolt"]
# How the products are ordered once no column is sorted: by the model's ordering again from
# Django 5.2, and before that by the primary key alone.
UNSORTED = ["Bolt", "Nut", "Washer"] if django.VERSION >= (5, 2) else NEWEST_FIRST
# Each way to change how a column is sorted.
SORT_METHODS = {
    "make_primary_sort": lambda column: column.make_primary_sort(),
    "set_sort_direction": lambda column: column.set_sort_direction("asc"),
    "remove_from_sort": lambda column: column.remove_from_sort(),
}


@pytest.fixture
def priced(db):
    """Three products, added in name order, whose prices and release dates differ."""
    rows = [
        ("Bolt", "3.00", datetime.date(2026, 3, 1)),
        ("Nut", "1.00", datetime.date(2026, 2, 1)),
        ("Washer", "2.00", datetime.date(2026, 1, 1)),
    ]
    return [
        Product.objects.create(name=name, sku=f"SKU-{name}", price=price, released_on=released)
        for name, price, released in rows
    ]


def sort_by(admin_ui, page, order):
    """Move ``page`` to the product changelist sorted by ``order``, as a click on a header
    would."""
    page.native.goto(admin_ui.absolute(f"{admin_ui.url.list(Product)}?o={order}"))


def test_the_sortable_columns_are_listed_in_the_order_shown(admin_ui, superuser, products):
    admin_ui.login(superuser)

    assert admin_ui.list(Product).sortable_columns == SORTABLE


def test_a_method_column_without_an_ordering_cannot_be_sorted(admin_ui, superuser, products):
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert page.has_column("price_with_tax")
    assert "price_with_tax" not in page.sortable_columns
    assert "documents" not in page.sortable_columns


def test_a_field_column_the_admin_leaves_out_of_sortable_by_cannot_be_sorted(
    admin_ui, superuser, feed
):
    """The feed's admin lets the user sort by the source and the two times only, and its two
    methods have no ordering."""
    admin_ui.login(superuser)

    page = admin_ui.list(Feed)

    assert page.has_column("mode")
    assert page.sortable_columns == ["source", "refreshed_at", "refresh_time"]


def test_a_user_without_actions_reads_the_same_sortable_columns(admin_ui, viewer, products):
    admin_ui.login(viewer)

    assert admin_ui.list(Product).sortable_columns == SORTABLE


def test_an_empty_changelist_has_no_sortable_columns(admin_ui, superuser):
    admin_ui.login(superuser)

    assert admin_ui.list(Product).sortable_columns == []


def test_a_page_that_did_not_open_cannot_list_its_sortable_columns(admin_ui, adder):
    admin_ui.login(adder)
    page = admin_ui.list(Product)

    with pytest.raises(LookupError, match="The page did not open"):
        _ = page.sortable_columns


@pytest.mark.parametrize("name", LABELS)
def test_a_column_reads_its_name_and_its_label(admin_ui, superuser, products, name):
    admin_ui.login(superuser)

    column = admin_ui.list(Product).column(name)

    assert column.name == name
    assert column.label == LABELS[name]


def test_a_column_reads_as_its_header_cell(admin_ui, superuser, products):
    admin_ui.login(superuser)

    column = admin_ui.list(Product).column("price")

    assert column.native.evaluate("cell => cell.tagName") == "TH"
    assert column.native.locator("div.text").text_content().strip() == "Price"


def test_a_column_shows_its_name_when_printed(admin_ui, superuser, products):
    admin_ui.login(superuser)

    assert repr(admin_ui.list(Product).column("price")) == "ChangelistColumn('price')"


def test_a_column_says_whether_it_can_be_sorted_as_the_page_lists_it(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    sortable = {name: page.column(name).sortable for name in page.columns}

    assert sortable == {name: name in SORTABLE for name in page.columns}


def test_a_user_without_actions_reads_the_same_column(admin_ui, viewer, products):
    admin_ui.login(viewer)

    column = admin_ui.list(Product).column("price")

    assert column.label == "Price"
    assert column.sortable is True


@pytest.mark.parametrize("name", ["color", "-price", "Price"])
def test_a_name_the_page_does_not_show_raises_listing_the_columns(
    admin_ui, superuser, products, name
):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    with pytest.raises(LookupError) as raised:
        page.column(name)

    assert str(raised.value) == f"No column named {name!r} here. Columns: {COLUMN_LIST}."


def test_an_empty_changelist_has_no_column_to_return(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    with pytest.raises(LookupError) as raised:
        page.column("price")

    assert str(raised.value) == "No column named 'price' here. The changelist shows no columns."


def test_a_page_that_did_not_open_has_no_column_to_return(admin_ui, adder):
    admin_ui.login(adder)
    page = admin_ui.list(Product)

    with pytest.raises(LookupError, match="The page did not open"):
        page.column("price")


def test_a_column_the_page_no_longer_shows_raises(admin_ui, superuser, products):
    """A search that finds nothing leaves the changelist without a table."""
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    column = page.column("price")

    page.search("nothing like it")

    with pytest.raises(LookupError, match="The page no longer shows the column 'price'"):
        _ = column.label


def test_a_column_keeps_working_after_the_page_loads_again(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    column = page.column("price")

    page.search("Bolt")

    assert column.label == "Price"
    assert column.sortable is True


def test_a_changelist_shows_the_model_ordering_on_its_column(admin_ui, superuser, products):
    """The product model is ordered by name, and only one column is sorted, so the page shows
    no priority number."""
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    name = page.column("name")

    assert page.sorted_columns == ["name"]
    assert name.sort_direction == "asc"
    assert name.sort_priority == 1
    assert name.native.locator(".sortpriority").count() == 0


def test_a_changelist_ordered_by_no_column_shows_none_sorted(admin_ui, superuser, feed):
    """The feed model has no ordering, so Django orders it by `-pk` alone, which it never
    marks."""
    admin_ui.login(superuser)
    page = admin_ui.list(Feed)

    assert page.sorted_columns == []
    assert page.column("source").sort_direction is None
    assert page.column("source").sort_priority is None


@pytest.mark.parametrize("user", PRICE_THEN_NAME)
def test_several_sorted_columns_are_read_in_priority_order(admin_ui, products, user, request):
    admin_ui.login(request.getfixturevalue(user))
    page = admin_ui.list(Product)

    sort_by(admin_ui, page, PRICE_THEN_NAME[user])
    price = page.column("price")
    name = page.column("name")

    assert page.sorted_columns == ["-price", "name"]
    assert price.sort_direction == "desc"
    assert price.sort_priority == 1
    assert name.sort_direction == "asc"
    assert name.sort_priority == 2


def test_a_sort_direction_equals_its_member_and_its_plain_string(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    sort_by(admin_ui, page, "-3.1")

    price = page.column("price").sort_direction
    name = page.column("name").sort_direction

    assert isinstance(price, SortDirection)
    assert price == SortDirection.DESCENDING
    assert price == "desc"
    assert price in {"desc"}
    assert isinstance(name, SortDirection)
    assert name == SortDirection.ASCENDING
    assert name == "asc"
    assert name in {"asc"}


@pytest.mark.parametrize("name", ["sku", "price_with_tax"])
def test_a_column_that_is_not_sorted_has_no_direction_or_priority(
    admin_ui, superuser, products, name
):
    """The SKU can be sorted but isn't, and the price with tax can't be."""
    admin_ui.login(superuser)
    column = admin_ui.list(Product).column(name)

    assert column.sort_direction is None
    assert column.sort_priority is None


def test_an_empty_changelist_has_no_sorted_columns(admin_ui, superuser):
    admin_ui.login(superuser)

    assert admin_ui.list(Product).sorted_columns == []


def test_a_page_that_did_not_open_cannot_list_its_sorted_columns(admin_ui, adder):
    admin_ui.login(adder)
    page = admin_ui.list(Product)

    with pytest.raises(LookupError, match="The page did not open"):
        _ = page.sorted_columns


def test_a_column_reads_how_it_is_sorted_now(admin_ui, superuser, products):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    name = page.column("name")

    sort_by(admin_ui, page, "-3.1")

    assert name.sort_direction == "asc"
    assert name.sort_priority == 2
    assert page.sorted_columns == ["-price", "name"]

    sort_by(admin_ui, page, "-1")

    assert name.sort_direction == "desc"
    assert name.sort_priority == 1
    assert page.sorted_columns == ["-name"]


def names(page):
    return [row["name"].value for row in page.rows]


def loads_nothing(page, change):
    """Whether ``change`` leaves the browser on the same document, which a marker set on it
    survives only then."""
    page.native.evaluate("window.notReloaded = true")
    change()
    return page.native.evaluate("window.notReloaded === true")


def test_making_an_unsorted_column_primary_sorts_by_it_first(admin_ui, superuser, priced):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    assert page.column("price").make_primary_sort() is None

    assert page.works
    assert page.sorted_columns == ["price", "name"]
    assert page.column("price").sort_direction == "asc"
    assert names(page) == BY_PRICE


@pytest.mark.parametrize("direction", ["desc", SortDirection.DESCENDING])
def test_a_column_is_made_primary_in_the_direction_asked(admin_ui, superuser, priced, direction):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    page.column("price").make_primary_sort(direction)

    assert page.sorted_columns == ["-price", "name"]
    assert names(page) == BY_PRICE_DESCENDING


@pytest.mark.parametrize(("direction", "expected"), [("asc", "name"), ("desc", "-name")])
def test_a_sorted_column_that_is_not_first_is_made_primary_in_the_direction_asked(
    admin_ui, superuser, priced, direction, expected
):
    """The name is sorted descending after the price, and comes first either way."""
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    sort_by(admin_ui, page, "3.-1")

    page.column("name").make_primary_sort(direction)

    assert page.sorted_columns == [expected, "price"]


def test_making_the_primary_column_primary_in_its_direction_loads_nothing(
    admin_ui, superuser, priced
):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    assert loads_nothing(page, lambda: page.column("name").make_primary_sort("asc"))
    assert page.sorted_columns == ["name"]


def test_making_the_primary_column_primary_the_other_way_flips_it(admin_ui, superuser, priced):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    page.column("name").make_primary_sort("desc")

    assert page.sorted_columns == ["-name"]
    assert names(page) == BY_NAME_DESCENDING


@pytest.mark.parametrize("method", ["make_primary_sort", "set_sort_direction"])
def test_a_direction_that_is_not_asc_or_desc_raises(admin_ui, superuser, priced, method):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    column = page.column("name")

    with pytest.raises(ValueError) as raised:
        loads_nothing(page, lambda: getattr(column, method)("up"))

    assert str(raised.value) == "'up' is not a sort direction. Use 'asc' or 'desc'."
    assert page.sorted_columns == ["name"]


@pytest.mark.parametrize(
    ("name", "expected"), [("price", ["-price", "name"]), ("name", ["price", "-name"])]
)
def test_setting_the_other_direction_flips_a_column_in_its_place(
    admin_ui, superuser, priced, name, expected
):
    """The price is first and the name second, and each keeps its place."""
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    sort_by(admin_ui, page, "3.1")

    assert page.column(name).set_sort_direction("desc") is None

    assert page.sorted_columns == expected


def test_setting_the_direction_a_column_has_loads_nothing(admin_ui, superuser, priced):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    assert loads_nothing(page, lambda: page.column("name").set_sort_direction("asc"))
    assert page.sorted_columns == ["name"]


def test_setting_the_direction_of_an_unsorted_column_raises(admin_ui, superuser, priced):
    """Django adds a column to the sort only as the first one."""
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    with pytest.raises(LookupError) as raised:
        page.column("price").set_sort_direction("desc")

    assert str(raised.value) == (
        "The column 'price' is not sorted, so it has no direction to set. Sort by it with "
        "make_primary_sort('desc'), which puts it first and keeps the other sorted columns "
        "after it."
    )
    assert page.sorted_columns == ["name"]


def test_removing_a_column_from_the_sort_moves_the_others_up(admin_ui, superuser, priced):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    sort_by(admin_ui, page, "-3.1")

    assert page.column("price").remove_from_sort() is None

    assert page.sorted_columns == ["name"]
    assert page.column("name").sort_priority == 1


def test_removing_the_last_sorted_column_leaves_no_column_marked(admin_ui, superuser, priced):
    """The headers mark none once the URL asks for an empty sort, whatever order Django's
    version then gives the records."""
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    page.column("name").remove_from_sort()

    assert page.sorted_columns == []
    assert names(page) == UNSORTED


def test_removing_a_column_that_is_not_sorted_loads_nothing(admin_ui, superuser, priced):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    assert loads_nothing(page, lambda: page.column("price").remove_from_sort())
    assert page.sorted_columns == ["name"]


@pytest.mark.parametrize("method", SORT_METHODS)
def test_a_column_that_cannot_be_sorted_raises_on_every_sort_change(
    admin_ui, superuser, priced, method
):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    with pytest.raises(LookupError) as raised:
        SORT_METHODS[method](page.column("price_with_tax"))

    assert str(raised.value) == "The column 'price_with_tax' cannot be sorted."
    assert page.sorted_columns == ["name"]


def test_one_column_object_keeps_sorting_across_page_loads(admin_ui, superuser, priced):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    price = page.column("price")

    price.make_primary_sort()
    price.set_sort_direction("desc")

    assert page.sorted_columns == ["-price", "name"]

    price.remove_from_sort()

    assert page.sorted_columns == ["name"]


def test_a_method_column_with_an_ordering_sorts_by_its_field(admin_ui, superuser, priced):
    """The released column sorts by the release date."""
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    page.column("is_released").make_primary_sort()

    assert page.sorted_columns == ["is_released", "name"]
    assert names(page) == BY_RELEASE


def test_a_sort_keeps_the_search_and_the_filters_applied(admin_ui, superuser, priced):
    """The term is in the name or the SKU of the bolt and the nut."""
    admin_ui.login(superuser)
    page = admin_ui.list(Product, search="t")
    page.filters["is_active"].apply("Yes")

    page.column("price").make_primary_sort("desc")

    assert page.search_term == "t"
    assert page.filters["is_active"].selected == "Yes"
    assert names(page) == ["Bolt", "Nut"]


def test_a_search_and_clearing_the_filters_keep_the_sort(admin_ui, superuser, priced):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    page.column("price").make_primary_sort("desc")

    page.search("t")

    assert page.sorted_columns == ["-price", "name"]

    page.filters["is_active"].apply("Yes")
    page.filters.clear()

    assert page.sorted_columns == ["-price", "name"]


def test_a_sort_after_the_session_ended_reports_the_refusal(admin_ui, superuser, priced):
    """The admin sends the browser to the login page after the first click, and the page
    stands for where it landed rather than clicking on."""
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    admin_ui.logout()

    page.column("price").make_primary_sort("desc")

    assert page.denied
    assert page.redirected
    assert page.destination == admin_ui.url.login()
    with pytest.raises(LookupError, match="The page did not open"):
        _ = page.sorted_columns
