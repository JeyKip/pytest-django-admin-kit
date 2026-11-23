"""The boxes the admin draws for `autocomplete_fields`: read as a select reads, with the choices
the admin's autocomplete view offers, and filled with any of them, whether the box held its
option before or not."""

import pytest

from django_admin_kit.fields import FieldChoice
from project.shop.models import Bundle, Product

# The admin's autocomplete view answers 20 options a page.
PAGE_SIZE = 20


@pytest.fixture
def bolt(db):
    return Product.objects.create(name="Bolt", sku="SKU-Bolt", price="10.00")


@pytest.fixture
def nut(db):
    return Product.objects.create(name="Nut", sku="SKU-Nut", price="10.00")


@pytest.fixture
def washer(db):
    return Product.objects.create(name="Washer", sku="SKU-Washer", price="10.00")


@pytest.fixture
def parts(db):
    """More products than the autocomplete view answers on one page, in the order it gives."""
    return [
        Product.objects.create(name=f"Part {number:02}", sku=f"SKU-{number}", price="1.00")
        for number in range(1, PAGE_SIZE + 2)
    ]


def choice(product):
    return str(product.pk), product.name


def test_an_empty_box_reads_as_its_blank_option(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Bundle)

    assert page.fields["lead"].value == ("", "")


def test_an_empty_many_to_many_box_reads_as_empty(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Bundle)

    assert page.fields["add_ons"].value == []


def test_a_box_reads_as_the_products_stored(admin_ui, superuser, bolt, nut, washer):
    """The admin draws the chosen products in their own order, by name."""
    bundle = Bundle.objects.create(name="Starter kit", lead=nut)
    bundle.add_ons.set([washer, bolt])
    admin_ui.login(superuser)

    page = admin_ui.edit(bundle)

    assert page.fields["lead"].value == choice(nut)
    assert page.fields["add_ons"].value == [choice(bolt), choice(washer)]


def test_the_choices_are_the_blank_option_then_every_product_offered(
    admin_ui, superuser, bolt, nut, washer
):
    admin_ui.login(superuser)

    page = admin_ui.create(Bundle)

    assert page.fields["lead"].choices == [("", ""), choice(bolt), choice(nut), choice(washer)]


def test_a_many_to_many_box_has_no_blank_choice(admin_ui, superuser, bolt, nut, washer):
    admin_ui.login(superuser)

    page = admin_ui.create(Bundle)

    assert page.fields["add_ons"].choices == [choice(bolt), choice(nut), choice(washer)]


def test_the_choices_hold_every_page_the_view_answers(admin_ui, superuser, parts):
    admin_ui.login(superuser)

    page = admin_ui.create(Bundle)

    assert page.fields["lead"].choices == [("", ""), *(choice(part) for part in parts)]


@pytest.mark.parametrize(
    "spell",
    [
        lambda product: product,
        lambda product: product.pk,
        lambda product: FieldChoice(str(product.pk), product.name),
    ],
    ids=["instance", "pk", "choice"],
)
def test_a_box_is_filled_with_a_product_it_had_no_option_for(admin_ui, superuser, nut, spell):
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)

    page.fields["lead"].fill(spell(nut))

    assert page.fields["lead"].value == choice(nut)


def test_a_box_is_filled_with_another_product_than_the_one_stored(
    admin_ui, superuser, bolt, washer
):
    bundle = Bundle.objects.create(name="Starter kit", lead=bolt)
    admin_ui.login(superuser)
    page = admin_ui.edit(bundle)

    page.fields["lead"].fill(washer)

    assert page.fields["lead"].value == choice(washer)


def test_none_puts_a_box_on_its_blank_option(admin_ui, superuser, bolt):
    bundle = Bundle.objects.create(name="Starter kit", lead=bolt)
    admin_ui.login(superuser)
    page = admin_ui.edit(bundle)

    page.fields["lead"].fill(None)

    assert page.fields["lead"].value == ("", "")


def test_a_value_the_view_does_not_offer_changes_nothing(admin_ui, superuser, bolt, nut, washer):
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)
    page.fields["lead"].fill(bolt)

    with pytest.raises(ValueError) as failure:
        page.fields["lead"].fill("Games")

    assert str(failure.value) == (
        f"The field 'lead' offers no option for 'Games'. "
        f"Options: '', '{bolt.pk}', '{nut.pk}', '{washer.pk}'."
    )
    assert page.fields["lead"].value == choice(bolt)


def test_a_many_to_many_box_is_filled_with_exactly_the_values_in_the_order_given(
    admin_ui, superuser, bolt, nut, washer
):
    bundle = Bundle.objects.create(name="Starter kit")
    bundle.add_ons.set([bolt])
    admin_ui.login(superuser)
    page = admin_ui.edit(bundle)

    page.fields["add_ons"].fill([washer, nut])

    assert page.fields["add_ons"].value == [choice(washer), choice(nut)]


def test_a_value_given_twice_is_chosen_once_in_a_many_to_many_box(admin_ui, superuser, nut):
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)

    page.fields["add_ons"].fill([nut, nut])

    assert page.fields["add_ons"].value == [choice(nut)]


@pytest.mark.parametrize("empty", [None, []], ids=["none", "empty list"])
def test_none_and_an_empty_list_clear_a_many_to_many_box(admin_ui, superuser, bolt, nut, empty):
    bundle = Bundle.objects.create(name="Starter kit")
    bundle.add_ons.set([bolt, nut])
    admin_ui.login(superuser)
    page = admin_ui.edit(bundle)

    page.fields["add_ons"].fill(empty)

    assert page.fields["add_ons"].value == []


def test_a_lone_value_is_refused_for_a_many_to_many_box(admin_ui, superuser, bolt):
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)

    with pytest.raises(TypeError) as failure:
        page.fields["add_ons"].fill(bolt)

    assert str(failure.value) == (
        f"The field 'add_ons' takes a list of values or None, not {bolt!r}. "
        f"A single value is written as [value]."
    )


def test_the_products_chosen_are_stored_once_saved(admin_ui, superuser, bolt, nut, washer):
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)
    page.populate(name="Starter kit", lead=nut, add_ons=[washer, bolt])

    assert page.save().success

    bundle = Bundle.objects.get()
    assert bundle.lead == nut
    assert list(bundle.add_ons.all()) == [bolt, washer]


def test_populate_fills_the_boxes_from_a_saved_instance(admin_ui, superuser, nut, washer):
    other = Bundle.objects.create(name="Starter kit", lead=washer)
    other.add_ons.set([nut])
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)

    page.populate(other)

    assert page.fields["lead"].value == choice(washer)
    assert page.fields["add_ons"].value == [choice(nut)]
