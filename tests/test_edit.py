"""Whether the change page opens for each user, and what happens when the object is gone."""

from project.shop.models import Product


def test_a_superuser_reaches_the_change_page(admin_ui, superuser, product):
    admin_ui.login(superuser)

    page = admin_ui.edit(product)

    assert page.works
    assert page.destination == admin_ui.url.edit(product)


def test_the_change_page_names_the_object(admin_ui, superuser, product):
    admin_ui.login(superuser)

    page = admin_ui.edit(product)

    assert page.title == "Change product"
    assert page.subtitle == "Widget"


def test_a_viewer_gets_the_page_read_only(admin_ui, viewer, product):
    """The title is how the admin tells the user what they may do here."""
    admin_ui.login(viewer)

    page = admin_ui.edit(product)

    assert page.works
    assert page.destination == admin_ui.url.edit(product)
    assert page.title == "View product"
    assert page.subtitle == "Widget"


def test_an_editor_gets_the_page_to_change(admin_ui, editor, product):
    admin_ui.login(editor)

    page = admin_ui.edit(product)

    assert page.works
    assert page.destination == admin_ui.url.edit(product)
    assert page.title == "Change product"
    assert page.subtitle == "Widget"


def test_a_user_who_may_only_add_is_refused_in_place(admin_ui, adder, product):
    admin_ui.login(adder)

    page = admin_ui.edit(product)

    assert page.denied
    assert page.status_code == 403
    assert page.destination == admin_ui.url.edit(product)


def test_a_refused_user_is_sent_to_the_login_page(admin_ui, customer, product):
    admin_ui.login(customer)

    page = admin_ui.edit(product)

    assert page.denied
    assert page.status_code == 200
    assert page.destination == admin_ui.url.login()


def test_an_object_that_no_longer_exists_is_missing_not_denied(admin_ui, superuser, product):
    """The admin sends a permitted user to the index with a message."""
    Product.objects.filter(pk=product.pk).delete()
    admin_ui.login(superuser)

    page = admin_ui.edit(product)

    assert page.missing
    assert not page.denied
    assert page.destination == admin_ui.url.index()
