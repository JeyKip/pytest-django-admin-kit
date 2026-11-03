"""The two lists the admin's script draws for `filter_horizontal` and `filter_vertical`,
which no built-in widget class reads or fills, so a project teaches them with its own."""

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


def test_a_filter_widget_is_read_by_no_built_in_class(admin_ui, superuser, category):
    admin_ui.login(superuser)
    page = admin_ui.create(Category)

    with pytest.raises(LookupError) as failure:
        _ = page.fields["see_also"].value

    assert str(failure.value) == (
        "No widget class can read the field 'see_also'. Add one for it to "
        "DJANGO_ADMIN_KIT['widgets']."
    )


def test_a_filter_widget_is_filled_by_no_built_in_class(admin_ui, superuser, category):
    admin_ui.login(superuser)
    page = admin_ui.create(Category)

    with pytest.raises(LookupError) as failure:
        page.fields["see_also"].fill([category])

    assert str(failure.value) == (
        "No widget class can fill the field 'see_also'. Add one for it to "
        "DJANGO_ADMIN_KIT['widgets']."
    )


@pytest.mark.parametrize("admin_ui_widgets", [Widgets([ChosenListWidget()])])
def test_a_project_class_reads_a_filter_widget(admin_ui, superuser, category):
    admin_ui.login(superuser)

    page = admin_ui.create(Category)

    assert page.fields["see_also"].value == []
    assert page.fields["see_also"].choices == [(str(category.pk), "Tools")]
