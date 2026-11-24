"""The two lists the admin's script draws for a form field of the project's own, as
`filter_horizontal` draws them: read and filled by the built-in widget class, unless a project
lists a class of its own for them, which goes first."""

import pytest

from django_admin_kit.fields import FieldChoice
from django_admin_kit.widgets import Widgets
from project.shop.models import Category


class ChosenListWidget:
    """The admin's two lists, read as the labels of the options chosen and offering the
    ones still available."""

    def marker(self, field):
        return f'select.filtered[name="{field.name}"]'

    def read(self, field):
        chosen = field.native.locator(f'select[name="{field.name}"] option')
        return [option.inner_text() for option in chosen.all()]

    def fill(self, field, value):
        raise NotImplementedError

    def choices(self, field):
        available = field.native.locator(f'select[name="{field.name}_old"] option')
        return [
            FieldChoice(option.get_attribute("value"), option.inner_text())
            for option in available.all()
        ]


def test_a_filter_widget_on_a_form_field_is_read_by_the_built_in_class(
    admin_ui, superuser, category
):
    admin_ui.login(superuser)

    page = admin_ui.create(Category)

    assert page.fields["see_also"].value == []
    assert page.fields["see_also"].choices == [(str(category.pk), "Tools")]


def test_a_filter_widget_on_a_form_field_is_filled_by_the_built_in_class(
    admin_ui, superuser, category
):
    admin_ui.login(superuser)
    page = admin_ui.create(Category)

    page.fields["see_also"].fill([category])

    assert page.fields["see_also"].value == [(str(category.pk), "Tools")]


@pytest.mark.parametrize("admin_ui_widgets", [Widgets([ChosenListWidget()])])
def test_a_project_class_reads_a_filter_widget_before_the_built_in_one(
    admin_ui, superuser, category
):
    """It reads the labels chosen, where the built-in class reads choices."""
    admin_ui.login(superuser)
    page = admin_ui.create(Category)

    page.fields["see_also"].native.locator('select[name="see_also_old"] option').dblclick()

    assert page.fields["see_also"].value == ["Tools"]
    assert page.fields["see_also"].choices == []
    assert page.fields["shelf"].choices == []
