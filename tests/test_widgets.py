"""Widget classes of the project's own, tried before the package's."""

import datetime
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import Permission, User

from django_admin_kit.widgets import SelectWidget, Widgets
from project.shop.kit_widgets import SwatchPickerWidget
from project.shop.models import Feed

REFRESHED_AT = datetime.datetime(2026, 1, 15, 9, 30)


class SwatchAsText(SwatchPickerWidget):
    """Recognizes the swatch picker as well, and reads its hidden input as text."""

    def read(self, field):
        return field.native.locator(f'input[name="{field.name}"]').input_value()


class BareSelectWidget(SelectWidget):
    """Reads a select as the value of the option chosen, without its label."""

    def read(self, field):
        return super().read(field).value


class SplitDateTimeWidget:
    """The admin's date and time inputs of one date-time: filled from a datetime and read
    as the pair of texts they hold."""

    def marker(self, field):
        return "p.datetime"

    def read(self, field):
        return tuple(self._part(field, index).input_value() for index in (0, 1))

    def fill(self, field, value):
        date, time = ("", "") if value is None else (f"{value:%Y-%m-%d}", f"{value:%H:%M:%S}")
        self._part(field, 0).fill(date)
        self._part(field, 1).fill(time)

    def _part(self, field, index):
        return field.native.locator(f'[name="{field.name}_{index}"]')


class NoMarker:
    def marker(self, field):
        return None

    def read(self, field):
        return None


@pytest.fixture(scope="session")
def admin_ui_widgets():
    """The swatch picker's widget class and one for the admin's split date-time in front
    of the package's, the way a project overrides the fixture for some of its tests."""
    return Widgets([SwatchPickerWidget(), SplitDateTimeWidget()])


@pytest.fixture
def green(feed):
    feed.color = "green"
    feed.save()
    return feed


@pytest.fixture
def unsaved_feed():
    """A feed with every field set, to fill a form from."""
    return Feed(
        source="catalog.csv",
        mode="replace",
        refreshed_at=REFRESHED_AT,
        refresh_time=datetime.time(6, 0),
        color="green",
    )


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


def test_a_widget_class_fills_the_field_and_reads_back_what_it_filled(admin_ui, superuser, green):
    admin_ui.login(superuser)

    page = admin_ui.edit(green)
    page.fields["color"].fill("blue")

    assert page.fields["color"].value == ("blue", "Blue")


def test_a_widget_class_decides_what_an_empty_value_fills(admin_ui, superuser, green):
    """The swatch picker's class clears the color, so a blank instance populates too."""
    admin_ui.login(superuser)

    page = admin_ui.edit(green)
    page.fields["color"].fill("")

    assert page.fields["color"].value is None
    assert page.fields["color"].native.locator("input").input_value() == ""


@pytest.mark.parametrize(
    "source",
    [
        {"source": "catalog.csv", "color": "red"},
        SimpleNamespace(source="catalog.csv", color="red"),
    ],
    ids=["dictionary", "namespace"],
)
def test_populate_fills_a_field_through_its_widget_class_with_the_rest(admin_ui, superuser, source):
    admin_ui.login(superuser)

    page = admin_ui.create(Feed)
    page.populate(source)

    assert page.fields["source"].value == "catalog.csv"
    assert page.fields["color"].value == ("red", "Red")


def test_a_widget_of_several_inputs_is_filled_from_one_value(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Feed)
    page.fields["refreshed_at"].fill(REFRESHED_AT)

    assert page.fields["refreshed_at"].value == ("2026-01-15", "09:30:00")


def test_populate_fills_every_field_of_a_model_instance(admin_ui, superuser, unsaved_feed):
    """The split date-time stopped this call before a widget class could fill it."""
    admin_ui.login(superuser)

    page = admin_ui.create(Feed)
    page.populate(unsaved_feed)

    assert {name: field.value for name, field in page.fields.items()} == {
        "source": "catalog.csv",
        "mode": ("replace", "Replace"),
        "refreshed_at": ("2026-01-15", "09:30:00"),
        "refresh_time": "06:00:00",
        "color": ("green", "Green"),
    }


def test_a_save_stores_what_the_widget_classes_filled(admin_ui, superuser, unsaved_feed):
    admin_ui.login(superuser)

    page = admin_ui.create(Feed)
    page.populate(unsaved_feed)
    page.save()

    assert Feed.objects.values("source", "mode", "refreshed_at", "refresh_time", "color").get() == {
        "source": "catalog.csv",
        "mode": "replace",
        "refreshed_at": REFRESHED_AT.replace(tzinfo=datetime.timezone.utc),
        "refresh_time": datetime.time(6, 0),
        "color": "green",
    }


def test_a_rejected_save_renders_back_what_the_widget_class_filled(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Feed)
    page.populate(source="", color="green")
    result = page.save()

    assert result.page.fields["source"].errors == ["This field is required."]
    assert result.page.fields["color"].value == ("green", "Green")


def test_a_widget_class_offers_the_choices_of_its_widget(admin_ui, superuser, green):
    admin_ui.login(superuser)

    page = admin_ui.edit(green)

    assert page.fields["color"].choices == [
        ("red", "Red"),
        ("green", "Green"),
        ("blue", "Blue"),
    ]
    assert page.fields["color"].value in page.fields["color"].choices


def test_a_widget_class_without_choices_offers_none(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Feed)

    assert page.fields["refreshed_at"].choices == []
