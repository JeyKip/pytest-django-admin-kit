"""Whether the add page opens for each user."""

from project.shop.models import Product


def test_a_superuser_reaches_the_add_page(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert page.works
    assert page.destination == admin_ui.url.create(Product)


def test_the_add_page_says_what_it_is(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Product)

    assert page.title == "Add product"
    assert page.subtitle == ""


def test_a_user_who_may_only_add_reaches_the_add_page(admin_ui, adder):
    admin_ui.login(adder)

    page = admin_ui.create(Product)

    assert page.works
    assert page.destination == admin_ui.url.create(Product)


def test_a_viewer_is_refused_in_place(admin_ui, viewer):
    admin_ui.login(viewer)

    page = admin_ui.create(Product)

    assert page.denied
    assert page.status_code == 403
    assert page.destination == admin_ui.url.create(Product)


def test_an_editor_is_refused_in_place(admin_ui, editor):
    """Changing products is one permission; adding one is another."""
    admin_ui.login(editor)

    page = admin_ui.create(Product)

    assert page.denied
    assert page.status_code == 403
    assert page.destination == admin_ui.url.create(Product)


def test_a_refused_user_is_sent_to_the_login_page(admin_ui, customer):
    admin_ui.login(customer)

    page = admin_ui.create(Product)

    assert page.denied
    assert page.status_code == 200
    assert page.destination == admin_ui.url.login()
