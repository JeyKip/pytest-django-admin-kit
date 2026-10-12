"""Widget classes of the project's own, tried before the package's."""

import pytest
from django.contrib.auth.models import Permission, User

from django_admin_kit.widgets import SelectWidget, Widgets
from project.shop.kit_widgets import SwatchPickerWidget


class SwatchAsText(SwatchPickerWidget):
    """Recognizes the swatch picker as well, and reads its hidden input as text."""

    def read(self, field):
        return field.native.locator(f'input[name="{field.name}"]').input_value()


class BareSelectWidget(SelectWidget):
    """Reads a select as the value of the option chosen, without its label."""

    def read(self, field):
        return super().read(field).value


class NoMarker:
    def marker(self, field):
        return None

    def read(self, field):
        return None


@pytest.fixture(scope="session")
def admin_ui_widgets():
    """The swatch picker's widget class in front of the package's, the way a project
    overrides the fixture for some of its tests."""
    return Widgets([SwatchPickerWidget()])


@pytest.fixture
def green(feed):
    feed.color = "green"
    feed.save()
    return feed


@pytest.fixture
def feed_viewer(db):
    """May look at feeds and nothing else."""
    user = User.objects.create_user(username="fay", is_staff=True)
    user.user_permissions.add(Permission.objects.get(codename="view_feed"))
    return user


def test_a_field_a_widget_class_recognizes_is_read_through_it(admin_ui, superuser, green):
    admin_ui.login(superuser)

    page = admin_ui.edit(green)

    assert page.fields["color"].value == ("green", "Green")


def test_a_field_it_does_not_recognize_is_read_by_the_package(admin_ui, superuser, green):
    admin_ui.login(superuser)

    page = admin_ui.edit(green)

    assert page.fields["source"].value == "catalog.csv"


@pytest.mark.parametrize("admin_ui_widgets", [Widgets([SwatchAsText(), SwatchPickerWidget()])])
def test_the_first_widget_class_that_recognizes_a_field_reads_it(admin_ui, superuser, green):
    admin_ui.login(superuser)

    page = admin_ui.edit(green)

    assert page.fields["color"].value == "green"


@pytest.mark.parametrize("admin_ui_widgets", [Widgets([BareSelectWidget()])])
def test_a_widget_class_recognizing_a_select_replaces_the_packages(
    admin_ui, superuser, released, category
):
    admin_ui.login(superuser)

    page = admin_ui.edit(released)

    assert page.fields["category"].value == str(category.pk)


@pytest.mark.parametrize("admin_ui_widgets", [Widgets([NoMarker()])])
def test_a_marker_that_is_no_selector_is_reported(admin_ui, superuser, green):
    admin_ui.login(superuser)

    page = admin_ui.edit(green)

    with pytest.raises(TypeError) as failure:
        _ = page.fields["source"].value
    assert str(failure.value) == (
        "NoMarker.marker() must return a non-empty CSS selector, not None."
    )


def test_a_rendered_only_field_is_read_by_its_rule_not_a_widget_class(admin_ui, feed_viewer, green):
    admin_ui.login(feed_viewer)

    page = admin_ui.edit(green)

    assert page.fields["color"].value == "green"
