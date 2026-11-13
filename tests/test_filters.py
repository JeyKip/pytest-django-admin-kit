"""The filters a changelist offers in its sidebar, grouped by the field they filter."""

from urllib.parse import parse_qs, urlsplit

import django
import pytest
from django.contrib.admin import EmptyFieldListFilter, RelatedOnlyFieldListFilter
from playwright.sync_api import Locator

from django_admin_kit.filters import FieldFilter, _field_of
from project.shop.admin import PriceInputFilter, PriceRangeFilter, ProductAdmin, StatusFilter
from project.shop.models import Category, Feed, Product, Review

# What a date filter offers on a field that may be empty.
DATE_CHOICES = [
    "Any date",
    "Today",
    "Past 7 days",
    "This month",
    "This year",
    "No date",
    "Has date",
]

# The parameters a filter's links send, and the field the filter is named after.
NAMES = {
    "a boolean": (Product, ["is_active__exact"], "is_active"),
    "a nullable boolean": (Product, ["featured__exact", "featured__isnull"], "featured"),
    "a date": (
        Product,
        ["released_on__gte", "released_on__lt", "released_on__isnull"],
        "released_on",
    ),
    "an empty filter": (Product, ["released_on__isempty"], "released_on"),
    "a nullable relation": (Product, ["category__id__exact", "category__isnull"], "category"),
    "a relation that can't be empty": (Review, ["product__id__exact"], "product"),
    "a text field": (Product, ["name"], "name"),
    "a field across a relation": (Product, ["category__name"], "category__name"),
    "a relation's target as such": (Product, ["category__id"], "category"),
    "a parameter that is no field": (Product, ["stock"], "stock"),
    "a custom range": (Product, ["price__gte", "price__lt"], "price"),
    "a custom range on other lookups": (Product, ["price__lte", "price__gt"], "price"),
    "names the ORM doesn't know": (Product, ["price__min", "price__max"], "price"),
    "names with nothing shared": (Product, ["price_min", "price_max"], "price_max"),
}


@pytest.fixture
def stocked(db):
    """Products in two categories, so the category filter has something to offer."""
    tools = Category.objects.create(name="Tools")
    toys = Category.objects.create(name="Toys")
    return [
        Product.objects.create(name="Bolt", sku="SKU-Bolt", price="5.00", category=tools),
        Product.objects.create(name="Kite", sku="SKU-Kite", price="20.00", category=toys),
    ]


@pytest.fixture
def list_filter(monkeypatch):
    """Sets the filters the product changelist offers, for one test."""
    return lambda *entries: monkeypatch.setattr(ProductAdmin, "list_filter", entries)


def links(element):
    """The labels of the links in a filter's list, as the user reads them."""
    return [" ".join(text.split()) for text in element.locator("a").all_text_contents()]


def click(page, parameter):
    """Follows the sidebar link that sends ``parameter``, as a user clicks it."""
    with page.native.expect_navigation():
        page.native.click(f"#changelist-filter a[href*='{parameter}']")


def test_a_changelist_with_filters_offers_filtering(admin_ui, superuser, stocked):
    admin_ui.login(superuser)

    assert admin_ui.list(Product).can_filter is True


def test_the_filters_are_listed_by_field_in_the_order_shown(admin_ui, superuser, stocked):
    """A filter of the project's own is listed by its parameter."""
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert list(page.filters) == ["is_active", "released_on", "category", "stock"]


def test_a_changelist_without_filters_offers_none(admin_ui, superuser, feed):
    admin_ui.login(superuser)

    page = admin_ui.list(Feed)

    assert page.can_filter is False
    assert page.filters == {}
    assert len(page.filters) == 0


def test_a_filter_with_nothing_to_offer_is_not_listed(admin_ui, superuser, products):
    """Without categories the admin draws no category filter, whatever `list_filter` says."""
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert list(page.filters) == ["is_active", "released_on", "stock"]


def test_a_field_without_filters_is_a_miss_that_lists_the_fields(admin_ui, superuser, stocked):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    with pytest.raises(KeyError) as failure:
        _ = page.filters["price"]

    assert failure.value.args[0] == (
        "No filter on a field named 'price' here. "
        "Fields: 'is_active', 'released_on', 'category', 'stock'."
    )


def test_a_miss_on_a_changelist_without_filters_says_there_are_none(admin_ui, superuser, feed):
    admin_ui.login(superuser)
    page = admin_ui.list(Feed)

    with pytest.raises(KeyError) as failure:
        _ = page.filters["source"]

    assert failure.value.args[0] == "No filter on a field named 'source' here. Fields: none."


def test_the_filters_read_as_a_mapping(admin_ui, superuser, stocked):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    filters = page.filters

    assert "is_active" in filters
    assert "price" not in filters
    assert filters.get("price") is None
    assert [group.name for group in filters.values()] == list(filters)


def test_a_field_with_one_filter_is_a_group_of_one(admin_ui, superuser, stocked):
    admin_ui.login(superuser)

    group = admin_ui.list(Product).filters["is_active"]

    assert group.name == "is_active"
    assert len(group) == 1
    assert isinstance(group[0], FieldFilter)


def test_a_group_of_one_has_the_list_of_its_filter_as_native(admin_ui, superuser, stocked):
    admin_ui.login(superuser)

    group = admin_ui.list(Product).filters["is_active"]

    assert isinstance(group.native, Locator)
    assert links(group.native) == ["All", "Yes", "No"]
    assert links(group[0].native) == ["All", "Yes", "No"]


def test_two_filters_on_one_field_make_one_group_in_the_order_shown(
    admin_ui, superuser, stocked, list_filter
):
    list_filter("is_active", "released_on", ("released_on", EmptyFieldListFilter))
    admin_ui.login(superuser)

    page = admin_ui.list(Product)
    group = page.filters["released_on"]

    assert list(page.filters) == ["is_active", "released_on"]
    assert len(group) == 2
    assert [links(element)[0] for element in group.native] == ["Any date", "All"]
    assert links(group[1].native) == ["All", "Empty", "Not empty"]


def test_filters_with_the_same_parameters_make_one_group(admin_ui, superuser, stocked, list_filter):
    """Django lets both through, and they act as one filter drawn twice."""
    list_filter("category", ("category", RelatedOnlyFieldListFilter))
    admin_ui.login(superuser)

    group = admin_ui.list(Product).filters["category"]

    assert len(group) == 2
    assert [links(element)[:3] for element in group.native] == [["All", "Tools", "Toys"]] * 2


def test_a_group_is_reached_from_either_end_and_in_a_loop(
    admin_ui, superuser, stocked, list_filter
):
    list_filter("released_on", ("released_on", EmptyFieldListFilter))
    admin_ui.login(superuser)

    group = admin_ui.list(Product).filters["released_on"]

    assert links(group[-1].native) == links(group[1].native)
    assert links(group[-2].native) == links(group[0].native)
    assert [links(item.native)[0] for item in group] == ["Any date", "All"]
    assert [links(item.native)[0] for item in group[1:]] == ["All"]


def test_an_index_past_the_end_of_a_group_raises(admin_ui, superuser, stocked):
    admin_ui.login(superuser)
    group = admin_ui.list(Product).filters["is_active"]

    with pytest.raises(IndexError) as failure:
        _ = group[1]

    assert str(failure.value) == "The field 'is_active' has 1 filter, so there is none at index 1."


def test_a_page_that_did_not_open_has_no_filters_to_read(admin_ui, adder):
    admin_ui.login(adder)
    page = admin_ui.list(Product)

    with pytest.raises(LookupError, match="The page did not open"):
        _ = page.filters
    with pytest.raises(LookupError, match="The page did not open"):
        _ = page.can_filter


def test_a_filter_held_after_the_browser_left_fails_at_once(admin_ui, left_for, superuser, stocked):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    filters = page.filters
    group = filters["is_active"]
    held = group[0]

    page.native.goto(admin_ui.absolute(admin_ui.url.index()))

    reads = (
        lambda: list(filters),
        lambda: filters["is_active"],
        lambda: len(group),
        lambda: group.native,
        lambda: held.native,
    )
    for read in reads:
        with pytest.raises(LookupError) as failure:
            read()
        assert str(failure.value) == left_for(admin_ui.url.index())


def test_held_filters_read_the_page_again(admin_ui, superuser, products):
    """A category gives the category filter something to offer, so the admin draws it."""
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    filters = page.filters
    assert "category" not in filters

    Product.objects.filter(name="Bolt").update(category=Category.objects.create(name="Tools"))
    with page.native.expect_navigation():
        page.native.reload()

    assert list(filters) == ["is_active", "released_on", "category", "stock"]
    assert len(filters["category"]) == 1


def test_a_custom_filter_on_a_field_is_listed_by_the_field(
    admin_ui, superuser, stocked, list_filter
):
    """Each of its links sends two parameters, which both name the price."""
    list_filter(("price", PriceRangeFilter))
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert list(page.filters) == ["price"]
    assert links(page.filters["price"].native) == ["All", "Under 10", "10 to 100"]


def test_a_filter_without_all_is_listed_by_the_parameter_its_links_change(
    admin_ui, superuser, stocked, list_filter
):
    """Every link sends the parameter, each with another value."""
    list_filter(StatusFilter, "is_active")
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert list(page.filters) == ["status", "is_active"]
    assert links(page.filters["status"].native) == ["Active", "Inactive"]


def test_a_filter_without_all_is_still_told_apart_once_applied(
    admin_ui, superuser, stocked, list_filter
):
    """The other filter's links then send its value too, the same in each of them."""
    list_filter(StatusFilter, "is_active")
    admin_ui.login(superuser)

    page = admin_ui.list(Product)
    with page.native.expect_navigation():
        page.native.click("#changelist-filter a[href*='status=active']")

    assert list(page.filters) == ["status", "is_active"]


def test_a_filter_drawn_with_inputs_is_not_listed(admin_ui, superuser, stocked, list_filter):
    """It has no choices to pick, so a test fills its inputs through `page.native`."""
    list_filter(("price", PriceInputFilter))
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert page.native.locator('#changelist-filter input[name="price__gte"]').count() == 1
    assert page.can_filter is False
    assert page.filters == {}


def test_a_filter_drawn_with_links_next_to_one_with_inputs_is_listed(
    admin_ui, superuser, stocked, list_filter
):
    list_filter(("price", PriceInputFilter), "is_active")
    admin_ui.login(superuser)

    page = admin_ui.list(Product)

    assert page.can_filter is True
    assert list(page.filters) == ["is_active"]


def test_each_filter_reads_its_choices_in_order(admin_ui, superuser, stocked):
    admin_ui.login(superuser)

    filters = admin_ui.list(Product).filters

    assert filters["is_active"].choices == ["All", "Yes", "No"]
    assert filters["released_on"].choices == DATE_CHOICES
    assert filters["category"].choices == ["All", "Tools", "Toys", "(none)"]
    assert filters["stock"].choices == ["All", "Low", "High"]
    assert filters["is_active"][0].choices == ["All", "Yes", "No"]


def test_a_custom_filter_on_a_field_reads_its_choices(admin_ui, superuser, stocked, list_filter):
    list_filter(("price", PriceRangeFilter))
    admin_ui.login(superuser)

    group = admin_ui.list(Product).filters["price"]

    assert group.choices == ["All", "Under 10", "10 to 100"]


def test_each_filter_reads_its_first_choice_as_selected_before_any_is_applied(
    admin_ui, superuser, stocked
):
    admin_ui.login(superuser)

    filters = admin_ui.list(Product).filters

    assert [group.selected for group in filters.values()] == ["All", "Any date", "All", "All"]


def test_a_filter_reads_the_choice_applied_and_the_others_keep_theirs(admin_ui, superuser, stocked):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    click(page, "is_active__exact=0")

    assert page.filters["is_active"].selected == "No"
    assert page.filters["is_active"][0].selected == "No"
    assert page.filters["released_on"].selected == "Any date"


def test_a_field_with_two_filters_reads_a_list_of_each(admin_ui, superuser, stocked, list_filter):
    list_filter("released_on", ("released_on", EmptyFieldListFilter))
    admin_ui.login(superuser)

    group = admin_ui.list(Product).filters["released_on"]

    assert group.choices == [DATE_CHOICES, ["All", "Empty", "Not empty"]]
    assert group.selected == ["Any date", "All"]


def test_the_date_filter_marks_nothing_while_the_empty_filter_on_its_field_is_applied(
    admin_ui, superuser, stocked, list_filter
):
    """Django compares every parameter of the field with the date filter's links."""
    list_filter("released_on", ("released_on", EmptyFieldListFilter))
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    click(page, "released_on__isempty=0")

    assert page.filters["released_on"].selected == [None, "Not empty"]
    assert page.filters["released_on"][0].selected is None


@pytest.mark.skipif(django.VERSION < (5, 0), reason="Django 5.0 added counts to filters.")
def test_counts_are_read_as_the_page_shows_them(admin_ui, superuser, stocked, monkeypatch):
    from django.contrib.admin import ShowFacets

    monkeypatch.setattr(ProductAdmin, "show_facets", ShowFacets.ALWAYS)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    click(page, "is_active__exact=0")

    assert page.filters["is_active"].choices == ["All", "Yes (2)", "No (0)"]
    assert page.filters["is_active"].selected == "No (0)"


def test_held_filters_read_the_selection_again(admin_ui, superuser, stocked):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    group = page.filters["is_active"]
    held = group[0]

    click(page, "is_active__exact=0")

    assert group.selected == "No"
    assert held.selected == "No"


def test_a_held_filter_whose_position_is_gone_raises(admin_ui, superuser, stocked, list_filter):
    list_filter("released_on", ("released_on", EmptyFieldListFilter))
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    held = page.filters["released_on"][1]

    list_filter("released_on")
    with page.native.expect_navigation():
        page.native.reload()

    with pytest.raises(LookupError) as failure:
        _ = held.selected

    assert str(failure.value) == (
        "The page no longer shows a filter on 'released_on' at index 1; it shows 1."
    )


def test_the_same_page_reads_the_results_of_a_filter(admin_ui, superuser, stocked):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    assert page.filters["category"].apply("Tools") is None

    assert page.works
    assert page.status_code == 200
    assert page.destination == admin_ui.url.list(Product)
    assert page.count == 1
    assert [row["name"].value for row in page.rows] == ["Bolt"]


def test_a_held_group_reads_the_choice_it_applied(admin_ui, superuser, stocked):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    group = page.filters["category"]

    group.apply("Toys")

    assert group.selected == "Toys"
    assert [row["name"].value for row in page.rows] == ["Kite"]


def test_a_filter_is_applied_through_its_index_in_a_group_of_one(admin_ui, superuser, stocked):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    page.filters["category"][0].apply("Toys")

    assert page.filters["category"].selected == "Toys"


def test_filters_on_two_fields_applied_one_after_the_other_both_hold(admin_ui, superuser, stocked):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    page.filters["category"].apply("Tools")
    page.filters["is_active"].apply("No")

    assert page.filters["category"].selected == "Tools"
    assert page.filters["is_active"].selected == "No"
    assert page.count == 0


def test_the_first_choice_clears_one_filter_and_keeps_the_other(admin_ui, superuser, stocked):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    page.filters["category"].apply("Tools")
    page.filters["is_active"].apply("Yes")

    page.filters["category"].apply("All")

    assert page.filters["category"].selected == "All"
    assert page.filters["is_active"].selected == "Yes"
    assert page.count == 2


def test_a_filter_keeps_a_search(admin_ui, superuser, stocked):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    page.search("Bolt")

    page.filters["category"].apply("Toys")

    assert page.search_term == "Bolt"
    assert page.count == 0


def test_a_search_keeps_a_filter(admin_ui, superuser, stocked):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    page.filters["category"].apply("Tools")

    page.search("Kite")

    assert page.filters["category"].selected == "Tools"
    assert page.count == 0


def test_a_choice_the_filter_does_not_offer_raises_and_nothing_is_clicked(
    admin_ui, superuser, stocked
):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    address = page.native.url

    for apply in (page.filters["is_active"].apply, page.filters["is_active"][0].apply):
        with pytest.raises(LookupError) as failure:
            apply("Maybe")
        assert str(failure.value) == (
            "No filter on 'is_active' offers 'Maybe'.\n\nChoices:\n    'All', 'Yes', 'No'"
        )

    assert page.native.url == address


def test_a_choice_that_is_no_string_matches_nothing(admin_ui, superuser, stocked):
    admin_ui.login(superuser)
    group = admin_ui.list(Product).filters["is_active"]

    with pytest.raises(LookupError, match="offers 1"):
        group.apply(1)


def test_a_label_one_filter_offers_twice_raises(admin_ui, superuser, stocked):
    """Two categories may share a name, and the filter then shows it twice."""
    Category.objects.create(name="Tools")
    admin_ui.login(superuser)
    group = admin_ui.list(Product).filters["category"]

    with pytest.raises(LookupError) as failure:
        group.apply("Tools")

    assert str(failure.value) == "The filter on 'category' offers 'Tools' more than once."


def test_a_choice_one_filter_of_a_group_offers_applies_there(
    admin_ui, superuser, stocked, list_filter
):
    list_filter("released_on", ("released_on", EmptyFieldListFilter))
    admin_ui.login(superuser)
    group = admin_ui.list(Product).filters["released_on"]

    group.apply("Has date")

    assert group.selected == ["Has date", "All"]


def test_a_choice_no_filter_of_a_group_offers_raises_listing_each(
    admin_ui, superuser, stocked, list_filter
):
    list_filter("released_on", ("released_on", EmptyFieldListFilter))
    admin_ui.login(superuser)
    group = admin_ui.list(Product).filters["released_on"]

    with pytest.raises(LookupError) as failure:
        group.apply("Maybe")

    assert str(failure.value) == (
        "No filter on 'released_on' offers 'Maybe'.\n"
        "\n"
        "Choices:\n"
        f"    [0] {', '.join(map(repr, DATE_CHOICES))}\n"
        "    [1] 'All', 'Empty', 'Not empty'"
    )


def test_a_choice_several_filters_of_a_group_offer_raises_naming_them(
    admin_ui, superuser, stocked, list_filter
):
    list_filter("category", ("category", RelatedOnlyFieldListFilter))
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    address = page.native.url

    with pytest.raises(LookupError) as failure:
        page.filters["category"].apply("Tools")

    assert str(failure.value) == (
        "The filters on 'category' at index 0 and 1 each offer 'Tools'. Apply it through one "
        "of them, such as page.filters['category'][0].apply('Tools')."
    )
    assert page.native.url == address


def test_a_filter_of_a_group_is_applied_through_its_index(
    admin_ui, superuser, stocked, list_filter
):
    """Both filters take the same parameter, and Django marks the choice on the first."""
    list_filter("category", ("category", RelatedOnlyFieldListFilter))
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    group = page.filters["category"]

    group[1].apply("Toys")

    assert [row["name"].value for row in page.rows] == ["Kite"]
    assert group.selected == ["Toys", "All"]


def test_empty_then_has_date_drops_empty_as_django_does(admin_ui, superuser, stocked, list_filter):
    """The date filter's links leave out every parameter of its field."""
    list_filter("released_on", ("released_on", EmptyFieldListFilter))
    admin_ui.login(superuser)
    group = admin_ui.list(Product).filters["released_on"]

    group.apply("Empty")
    group.apply("Has date")

    assert group.selected == ["Has date", "All"]


def test_has_date_then_empty_keeps_both_as_django_does(admin_ui, superuser, stocked, list_filter):
    """The empty filter's links keep the date filter's parameter, which the date filter then
    no longer marks."""
    list_filter("released_on", ("released_on", EmptyFieldListFilter))
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    group = page.filters["released_on"]

    group.apply("Has date")
    group.apply("Empty")

    # The date filter marks a choice only when a link of its own sends exactly the field's
    # parameters in the URL, and none of its links sends `released_on__isempty`.
    assert group.selected == [None, "Empty"]
    assert parse_qs(urlsplit(page.native.url).query) == {
        "released_on__isempty": ["1"],
        "released_on__isnull": ["False"],
    }


def test_a_custom_filter_sends_both_of_its_parameters_in_one_click(
    admin_ui, superuser, stocked, list_filter
):
    list_filter(("price", PriceRangeFilter))
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    page.filters["price"].apply("Under 10")

    assert page.filters["price"].selected == "Under 10"
    assert [row["name"].value for row in page.rows] == ["Bolt"]
    assert "price__gte=0" in page.native.url
    assert "price__lt=10" in page.native.url


@pytest.mark.skipif(django.VERSION < (5, 0), reason="Django 5.0 added counts to filters.")
def test_a_choice_applies_without_its_count(admin_ui, superuser, stocked, monkeypatch):
    from django.contrib.admin import ShowFacets

    monkeypatch.setattr(ProductAdmin, "show_facets", ShowFacets.ALWAYS)
    admin_ui.login(superuser)
    page = admin_ui.list(Product)

    page.filters["is_active"].apply("Yes")

    assert page.filters["is_active"].selected == "Yes (2)"
    assert page.count == 2


@pytest.mark.skipif(django.VERSION < (4, 1), reason="Django 4.1 made filters collapsible.")
def test_a_collapsed_filter_still_applies(admin_ui, superuser, stocked):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    group = page.filters["is_active"]
    group.native.evaluate("ul => { ul.closest('details').open = false; }")
    assert not group.native.locator("a").first.is_visible()

    group.apply("No")

    assert group.selected == "No"


def test_a_filter_applied_after_the_session_ended_leaves_the_page_denied(
    admin_ui, superuser, stocked
):
    admin_ui.login(superuser)
    page = admin_ui.list(Product)
    group = page.filters["category"]

    admin_ui.logout()
    group.apply("Tools")

    assert page.denied
    assert page.redirected
    assert page.destination == admin_ui.url.login()


@pytest.mark.parametrize(("model", "parameters", "name"), NAMES.values(), ids=NAMES.keys())
def test_a_filter_is_named_after_the_field_its_parameters_share(model, parameters, name):
    assert _field_of(model, parameters) == name
