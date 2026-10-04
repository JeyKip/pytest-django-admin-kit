"""Deleting an object in the admin's two steps: following the delete link from its edit page
to the confirmation, and confirming there."""

import pytest

from django_admin_kit.pages import DeletePage
from project.shop.models import Product


@pytest.fixture
def editing(admin_ui, superuser, product):
    """A product's edit page, which links to deleting it."""
    admin_ui.login(superuser)
    return admin_ui.edit(product)


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
