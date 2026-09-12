"""Whether the delete confirmation opens for each user, and what happens when the
object is gone."""

from datetime import date

import django

from project.shop.models import Product


def test_a_superuser_reaches_the_confirmation(admin_ui, superuser, product):
    admin_ui.login(superuser)

    page = admin_ui.delete(product)

    assert page.works
    assert page.destination == admin_ui.url.delete(product)


def test_the_confirmation_says_what_it_is(admin_ui, superuser, product):
    """Django 5.2 changed the title from a question to a verb. The package reports
    what the admin renders, so the suite proves the reader on both wordings."""
    admin_ui.login(superuser)

    page = admin_ui.delete(product)

    assert page.title == ("Delete" if django.VERSION >= (5, 2) else "Are you sure?")
    assert page.subtitle == ""


def test_a_viewer_is_refused_in_place(admin_ui, viewer, product):
    admin_ui.login(viewer)

    page = admin_ui.delete(product)

    assert page.denied
    assert page.status_code == 403
    assert page.destination == admin_ui.url.delete(product)


def test_an_editor_is_refused_in_place(admin_ui, editor, product):
    """Changing an object is one permission; deleting it is another."""
    admin_ui.login(editor)

    page = admin_ui.delete(product)

    assert page.denied
    assert page.status_code == 403
    assert page.destination == admin_ui.url.delete(product)


def test_a_user_who_may_only_add_is_refused_in_place(admin_ui, adder, product):
    admin_ui.login(adder)

    page = admin_ui.delete(product)

    assert page.denied
    assert page.status_code == 403
    assert page.destination == admin_ui.url.delete(product)


def test_a_refused_user_is_sent_to_the_login_page(admin_ui, customer, product):
    admin_ui.login(customer)

    page = admin_ui.delete(product)

    assert page.denied
    assert page.status_code == 200
    assert page.destination == admin_ui.url.login()


def test_an_object_that_no_longer_exists_is_missing_not_denied(admin_ui, superuser, product):
    Product.objects.filter(pk=product.pk).delete()
    admin_ui.login(superuser)

    page = admin_ui.delete(product)

    assert page.missing
    assert not page.denied
    assert page.destination == admin_ui.url.index()


def test_the_admin_may_refuse_one_object_and_allow_another(admin_ui, superuser, product):
    """The shop's rule: a released product stays on record. Same user, two answers."""
    released = Product.objects.create(
        name="Gadget", sku="SKU-2", price="10.00", released_on=date(2026, 1, 1)
    )
    admin_ui.login(superuser)

    assert admin_ui.delete(product).works

    page = admin_ui.delete(released)

    assert page.denied
    assert page.status_code == 403


def test_a_refused_user_is_not_told_whether_the_object_exists(admin_ui, viewer, product):
    """The admin checks permission before existence, so the refusal looks the same."""
    Product.objects.filter(pk=product.pk).delete()
    admin_ui.login(viewer)

    page = admin_ui.delete(product)

    assert page.denied
    assert not page.missing
