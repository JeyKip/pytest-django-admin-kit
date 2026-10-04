"""Deleting an object in the admin's two steps: following the delete link from its edit page
to the confirmation, and confirming there."""

import pytest

from django_admin_kit.pages import ChangelistPage, DeletePage
from project.shop.models import Category, Product


@pytest.fixture
def editing(admin_ui, superuser, product):
    """A product's edit page, which links to deleting it."""
    admin_ui.login(superuser)
    return admin_ui.edit(product)


@pytest.fixture
def confirming(admin_ui, superuser, product):
    """The page that asks whether to delete a product nothing depends on."""
    admin_ui.login(superuser)
    return admin_ui.delete(product)


@pytest.fixture
def protected(admin_ui, superuser, released, category):
    """The page that asks whether to delete a category the released product uses, which
    the product protects."""
    admin_ui.login(superuser)
    return admin_ui.delete(category)


def test_deleting_from_the_edit_page_opens_the_confirmation(admin_ui, product, editing):
    confirmation = editing.delete()

    assert isinstance(confirmation, DeletePage)
    assert confirmation.works
    assert confirmation.destination == admin_ui.url.delete(product)


def test_deleting_from_the_edit_page_deletes_nothing_yet(product, editing):
    editing.delete()

    assert Product.objects.filter(pk=product.pk).exists()


def test_the_edit_page_is_left_for_the_confirmation(admin_ui, left_for, product, editing):
    editing.delete()

    with pytest.raises(LookupError) as failure:
        bool(editing.works)

    assert str(failure.value) == left_for(admin_ui.url.delete(product))


def test_a_user_who_may_not_delete_has_no_delete_link_to_follow(admin_ui, editor, product):
    admin_ui.login(editor)
    page = admin_ui.edit(product)

    with pytest.raises(LookupError) as failure:
        page.delete()

    assert str(failure.value) == "The page offers no delete link."
    assert page.works


def test_confirming_deletes_the_object(product, confirming):
    result = confirming.confirm_deleting()

    assert result.success
    assert not Product.objects.filter(pk=product.pk).exists()


def test_confirming_is_redirected_to_the_changelist(confirming):
    result = confirming.confirm_deleting()

    assert result.redirected_to_list(Product)
    assert isinstance(result.page, ChangelistPage)
    assert result.page.works


def test_the_confirmation_is_left_once_confirmed(admin_ui, left_for, confirming):
    confirming.confirm_deleting()

    with pytest.raises(LookupError) as failure:
        bool(confirming.works)

    assert str(failure.value) == left_for(admin_ui.url.list(Product))


def test_the_confirmation_reached_from_the_edit_page_confirms_the_same(product, editing):
    result = editing.delete().confirm_deleting()

    assert result.success
    assert not Product.objects.filter(pk=product.pk).exists()


def test_a_page_that_deletes_nothing_protected_can_be_confirmed(confirming):
    assert confirming.can_confirm_deleting


def test_an_object_others_protect_cannot_be_confirmed(protected):
    assert protected.works
    assert not protected.can_confirm_deleting


def test_confirming_what_cannot_be_confirmed_deletes_nothing(category, protected):
    with pytest.raises(LookupError) as failure:
        protected.confirm_deleting()

    assert str(failure.value) == "The page offers no way to confirm the deletion."
    assert Category.objects.filter(pk=category.pk).exists()


def test_a_refused_confirmation_has_nothing_to_confirm_to_read(admin_ui, viewer, product):
    admin_ui.login(viewer)
    page = admin_ui.delete(product)

    with pytest.raises(LookupError) as failure:
        bool(page.can_confirm_deleting)

    assert str(failure.value) == (
        "The page did not open, so there is nothing to read from it. "
        f"Status 403, at {admin_ui.url.delete(product)}."
    )
