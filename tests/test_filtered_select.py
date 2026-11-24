"""The two lists the admin's script draws for `filter_horizontal` and `filter_vertical`: read
as the choices in the chosen list, as shown, and filled by moving options between the lists,
so the chosen list holds exactly the values given, in that order."""

import pytest

from project.shop.models import Bundle, Category

# Counts the double-clicks the page gets from now on, so a test sees whether a fill moved
# anything.
COUNT_DOUBLE_CLICKS = """() => {
    window.doubleClicks = 0;
    document.addEventListener("dblclick", () => window.doubleClicks++, true);
}"""


@pytest.fixture
def garden(db):
    return Category.objects.create(name="Garden")


@pytest.fixture
def tools(db):
    return Category.objects.create(name="Tools")


@pytest.fixture
def toys(db):
    return Category.objects.create(name="Toys")


def choice(category):
    return str(category.pk), category.name


def test_two_lists_with_nothing_chosen_read_as_empty(admin_ui, superuser, tools):
    admin_ui.login(superuser)

    page = admin_ui.create(Bundle)

    assert page.fields["categories"].value == []


def test_two_lists_read_as_the_chosen_list_shows_them(admin_ui, superuser, garden, tools, toys):
    """On a page just opened, the chosen list is in the categories' order, by name."""
    bundle = Bundle.objects.create(name="Starter kit")
    bundle.categories.set([toys, tools])
    admin_ui.login(superuser)

    page = admin_ui.edit(bundle)

    assert page.fields["categories"].value == [choice(tools), choice(toys)]


def test_the_choices_are_the_available_options_then_the_chosen_ones(
    admin_ui, superuser, garden, tools, toys
):
    bundle = Bundle.objects.create(name="Starter kit")
    bundle.categories.set([garden])
    admin_ui.login(superuser)

    page = admin_ui.edit(bundle)

    assert page.fields["categories"].choices == [choice(tools), choice(toys), choice(garden)]


def test_the_choices_keep_their_options_in_the_order_a_fill_left_them(
    admin_ui, superuser, garden, tools, toys
):
    """A moved option goes to the end of the other list, and the admin sorts neither."""
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)
    offered = set(page.fields["categories"].choices)

    page.fields["categories"].fill([toys, garden])

    assert page.fields["categories"].choices == [choice(tools), choice(toys), choice(garden)]
    assert set(page.fields["categories"].choices) == offered


def test_two_lists_are_filled_with_the_values_in_the_order_given(
    admin_ui, superuser, garden, tools, toys
):
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)

    page.fields["categories"].fill([toys, garden.pk, str(tools.pk)])

    assert page.fields["categories"].value == [choice(toys), choice(garden), choice(tools)]


def test_two_lists_are_filled_with_exactly_the_values_given(admin_ui, superuser, tools, toys):
    """An option chosen before is chosen again only when it is given."""
    bundle = Bundle.objects.create(name="Starter kit")
    bundle.categories.set([tools, toys])
    admin_ui.login(superuser)
    page = admin_ui.edit(bundle)

    page.fields["categories"].fill([toys])

    assert page.fields["categories"].value == [choice(toys)]


def test_two_lists_are_filled_with_their_own_choices(admin_ui, superuser, garden, tools):
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)

    page.fields["categories"].fill(page.fields["categories"].choices)

    assert page.fields["categories"].value == [choice(garden), choice(tools)]


def test_a_value_given_twice_is_chosen_once(admin_ui, superuser, tools, toys):
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)

    page.fields["categories"].fill([toys, toys])

    assert page.fields["categories"].value == [choice(toys)]


def test_the_values_already_chosen_in_that_order_move_nothing(admin_ui, superuser, tools, toys):
    bundle = Bundle.objects.create(name="Starter kit")
    bundle.categories.set([tools, toys])
    admin_ui.login(superuser)
    page = admin_ui.edit(bundle)
    page.native.evaluate(COUNT_DOUBLE_CLICKS)

    page.fields["categories"].fill([tools, toys])

    assert page.native.evaluate("window.doubleClicks") == 0
    assert page.fields["categories"].value == [choice(tools), choice(toys)]


@pytest.mark.parametrize("empty", [None, []], ids=["none", "empty list"])
def test_none_and_an_empty_list_clear_two_lists(admin_ui, superuser, tools, toys, empty):
    bundle = Bundle.objects.create(name="Starter kit")
    bundle.categories.set([tools, toys])
    admin_ui.login(superuser)
    page = admin_ui.edit(bundle)

    page.fields["categories"].fill(empty)

    assert page.fields["categories"].value == []


def test_a_lone_value_is_refused_for_two_lists(admin_ui, superuser, tools):
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)

    with pytest.raises(TypeError) as failure:
        page.fields["categories"].fill(tools)

    assert str(failure.value) == (
        f"The field 'categories' takes a list of values or None, not {tools!r}. "
        f"A single value is written as [value]."
    )


def test_a_value_two_lists_do_not_offer_moves_nothing(admin_ui, superuser, garden, tools):
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)
    page.fields["categories"].fill([tools])

    with pytest.raises(ValueError) as failure:
        page.fields["categories"].fill([garden, "Games"])

    assert str(failure.value) == (
        f"The field 'categories' offers no option for 'Games'. "
        f"Options: '{garden.pk}', '{tools.pk}'."
    )
    assert page.fields["categories"].value == [choice(tools)]


def test_stacked_lists_are_read_and_filled_the_same_way(admin_ui, superuser, garden, tools):
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)

    page.fields["sections"].fill([tools, garden])

    assert page.fields["sections"].value == [choice(tools), choice(garden)]
    assert page.fields["sections"].choices == [choice(tools), choice(garden)]


def test_the_chosen_list_is_stored_once_saved(admin_ui, superuser, garden, tools, toys):
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)
    page.populate(name="Starter kit", categories=[toys, garden], sections=[tools])

    assert page.save().success

    bundle = Bundle.objects.get()
    assert list(bundle.categories.all()) == [garden, toys]
    assert list(bundle.sections.all()) == [tools]


def test_populate_fills_two_lists_from_a_saved_instance(admin_ui, superuser, tools, toys):
    other = Bundle.objects.create(name="Starter kit")
    other.categories.set([toys])
    other.sections.set([tools])
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)

    page.populate(other)

    assert page.fields["categories"].value == [choice(toys)]
    assert page.fields["sections"].value == [choice(tools)]


def test_a_rejected_form_renders_the_chosen_list_back(admin_ui, superuser, tools, toys):
    """The name is required, so leaving it empty gets the form rejected."""
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)
    page.fields["categories"].fill([toys])

    result = page.save()

    assert not result.success
    assert result.page.fields["categories"].value == [choice(toys)]
