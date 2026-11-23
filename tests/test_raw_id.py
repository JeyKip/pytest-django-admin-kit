"""The inputs the admin draws for `raw_id_fields`: read as the ids they hold, as typed, and
filled with ids, a model instance written as its pk."""

import pytest

from django_admin_kit.fields import FieldChoice
from project.shop.models import Bundle, Product


@pytest.fixture
def bolt(db):
    return Product.objects.create(name="Bolt", sku="SKU-Bolt", price="10.00")


@pytest.fixture
def nut(db):
    return Product.objects.create(name="Nut", sku="SKU-Nut", price="10.00")


def test_an_empty_raw_id_input_reads_as_empty_text(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Bundle)

    assert page.fields["replacement"].value == ""
    assert page.fields["spares"].value == ""


def test_a_raw_id_input_reads_as_the_ids_stored(admin_ui, superuser, bolt, nut):
    """The admin joins the ids of a many-to-many field in their objects' order, by name."""
    bundle = Bundle.objects.create(name="Starter kit", replacement=nut)
    bundle.spares.set([nut, bolt])
    admin_ui.login(superuser)

    page = admin_ui.edit(bundle)

    assert page.fields["replacement"].value == str(nut.pk)
    assert page.fields["spares"].value == f"{bolt.pk},{nut.pk}"


@pytest.mark.parametrize(
    "spell",
    [
        lambda product: product,
        lambda product: product.pk,
        lambda product: str(product.pk),
        lambda product: FieldChoice(str(product.pk), product.name),
    ],
    ids=["instance", "int", "text", "choice"],
)
def test_a_raw_id_input_is_filled_with_the_id_of_a_value(admin_ui, superuser, nut, spell):
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)

    page.fields["replacement"].fill(spell(nut))

    assert page.fields["replacement"].value == str(nut.pk)


def test_a_many_to_many_raw_id_input_is_filled_with_a_list_joined_by_commas(
    admin_ui, superuser, bolt, nut
):
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)

    page.fields["spares"].fill([nut, bolt.pk])

    assert page.fields["spares"].value == f"{nut.pk},{bolt.pk}"


def test_a_many_to_many_raw_id_input_takes_text_as_is(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)

    page.fields["spares"].fill("3, 5")

    assert page.fields["spares"].value == "3, 5"


def test_a_list_is_refused_for_a_foreign_key_raw_id_input(admin_ui, superuser, bolt, nut):
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)

    with pytest.raises(TypeError) as failure:
        page.fields["replacement"].fill([bolt, nut])

    assert str(failure.value) == (
        f"The field 'replacement' takes one id or None, not the list {[bolt, nut]!r}."
    )
    assert page.fields["replacement"].value == ""


@pytest.mark.parametrize("empty", [None, ""], ids=["none", "empty text"])
def test_none_and_empty_text_empty_a_raw_id_input(admin_ui, superuser, nut, empty):
    bundle = Bundle.objects.create(name="Starter kit", replacement=nut)
    admin_ui.login(superuser)
    page = admin_ui.edit(bundle)

    page.fields["replacement"].fill(empty)

    assert page.fields["replacement"].value == ""


@pytest.mark.parametrize("empty", [None, "", []], ids=["none", "empty text", "empty list"])
def test_none_empty_text_and_an_empty_list_empty_a_many_to_many_raw_id_input(
    admin_ui, superuser, bolt, empty
):
    bundle = Bundle.objects.create(name="Starter kit")
    bundle.spares.set([bolt])
    admin_ui.login(superuser)
    page = admin_ui.edit(bundle)

    page.fields["spares"].fill(empty)

    assert page.fields["spares"].value == ""


def test_the_ids_typed_are_stored_once_saved(admin_ui, superuser, bolt, nut):
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)
    page.populate(name="Starter kit", replacement=bolt, spares=[nut, bolt])

    assert page.save().success

    bundle = Bundle.objects.get()
    assert bundle.replacement == bolt
    assert list(bundle.spares.all()) == [bolt, nut]


def test_populate_fills_raw_id_inputs_from_a_saved_instance(admin_ui, superuser, bolt, nut):
    other = Bundle.objects.create(name="Starter kit", replacement=nut)
    other.spares.set([bolt, nut])
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)

    page.populate(other)

    assert page.fields["replacement"].value == str(nut.pk)
    assert page.fields["spares"].value == f"{bolt.pk},{nut.pk}"
