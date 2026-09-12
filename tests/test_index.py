"""What the admin index lists for each user, read from the rendered page.

The default site registers Product from the test project and User and Group from
`django.contrib.auth`, which gives two apps and one app with two models.
"""

import pytest
from django.contrib.auth.models import Group, User

from project.shop.models import Product


def test_a_superuser_sees_every_app_and_model_in_the_admins_order(admin_ui, superuser):
    """Apps alphabetically by name, models by verbose name within an app."""
    admin_ui.login(superuser)

    page = admin_ui.index()

    assert page.apps == ["Authentication and Authorization", "Shop"]
    assert page.models == [Group, User, Product]
    assert page.models_for("Authentication and Authorization") == [Group, User]
    assert page.models_for("Shop") == [Product]


def test_an_app_the_index_does_not_show_is_reported_not_guessed(admin_ui, viewer):
    admin_ui.login(viewer)

    with pytest.raises(LookupError) as error:
        admin_ui.index().models_for("Billing")

    message = str(error.value)
    assert "no app named 'Billing'" in message
    assert "'Shop'" in message  # what it does show, so the mistake is obvious


def test_an_empty_index_says_so_when_asked_for_an_app(admin_ui, outsider):
    admin_ui.login(outsider)

    with pytest.raises(LookupError, match=r"no app named 'Shop'\. Shown: none\."):
        admin_ui.index().models_for("Shop")


def test_a_user_sees_only_the_apps_and_models_they_have_a_permission_on(admin_ui, viewer):
    admin_ui.login(viewer)

    page = admin_ui.index()

    assert page.apps == ["Shop"]
    assert page.models == [Product]


def test_a_model_the_user_may_only_add_is_still_listed(admin_ui, adder):
    """The admin lists it without a changelist link, so links are not what is read."""
    admin_ui.login(adder)

    page = admin_ui.index()

    assert page.apps == ["Shop"]
    assert page.models == [Product]


def test_a_model_the_user_may_not_see_is_not_listed(admin_ui, outsider):
    admin_ui.login(outsider)

    page = admin_ui.index()

    assert page.works
    assert page.apps == []
    assert page.models == []


def test_a_refused_user_has_nothing_to_read(admin_ui, customer):
    """They landed on the login page, which lists no models. Reading it as an empty
    index would let `apps == []` pass for a user who never saw the index."""
    admin_ui.login(customer)

    page = admin_ui.index()

    assert page.denied
    for read in (
        lambda: page.apps,
        lambda: page.models,
        lambda: page.models_for("Shop"),
        lambda: page.title,
        lambda: page.subtitle,
    ):
        with pytest.raises(LookupError, match=r"did not open.*Status 200, at /admin/login/"):
            read()


def test_the_index_says_what_it_is(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.index()

    assert page.title == "Site administration"
    assert page.subtitle == ""
