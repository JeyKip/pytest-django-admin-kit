"""The widget classes that read and fill a form's controls.

A widget class recognizes its widget by a marker, a CSS selector found inside a field's
box, and says how to read the field and how to fill it. The marker only picks the
class: ``read`` and ``fill`` get the whole field and find their own elements in its box.
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Iterable, Protocol

from django.db.models import Model
from django.utils import timezone
from playwright.sync_api import Locator

from .fields import FieldChoice
from .rendered import text_of

if TYPE_CHECKING:
    from .fields import FormField


class Widget(Protocol):
    """What the package asks of a widget class. ``choices(field)`` is optional."""

    def marker(self, field: FormField) -> str: ...

    def read(self, field: FormField) -> Any: ...

    def fill(self, field: FormField, value: Any) -> None: ...


class CheckboxWidget:
    """A checkbox, read and filled as a boolean."""

    def marker(self, field: FormField) -> str:
        return f'input[type="checkbox"][name="{field.name}"]'

    def read(self, field: FormField) -> bool:
        return self._control(field).is_checked()

    def fill(self, field: FormField, value: Any) -> None:
        self._control(field).set_checked(bool(value))

    def _control(self, field: FormField) -> Locator:
        return field.native.locator(f'input[type="checkbox"][name="{field.name}"]')


class SelectWidget:
    """A select, read as the ``FieldChoice`` chosen and filled with the option that
    stands for a value."""

    def marker(self, field: FormField) -> str:
        return f'select[name="{field.name}"]'

    def read(self, field: FormField) -> FieldChoice:
        option = self._control(field).locator("option:checked")
        return FieldChoice(option.get_attribute("value") or "", text_of(option))

    def fill(self, field: FormField, value: Any) -> None:
        option = self._option(field, value)
        # An option is asked for by its value, except the blank one, whose value is the
        # empty string: the browser layer reads that as "select nothing" on the versions
        # that still run on Python 3.8, so it is asked for by its label.
        if option.value:
            self._control(field).select_option(value=option.value)
        else:
            self._control(field).select_option(label=option.label)

    def choices(self, field: FormField) -> list[FieldChoice]:
        """The options the select offers, in order, the blank one included."""
        return [
            FieldChoice(option.get_attribute("value") or "", text_of(option))
            for option in self._control(field).locator("option").all()
        ]

    def _option(self, field: FormField, value: Any) -> FieldChoice:
        """The option that stands for ``value``, among the ones the select offers."""
        offered = {choice.value: choice for choice in self.choices(field)}
        for spelling in _option_spellings(value):
            if spelling in offered:
                return offered[spelling]
        raise ValueError(
            f"The field {field.name!r} offers no option for {value!r}. Options: "
            f"{', '.join(repr(option) for option in offered) or 'none'}."
        )

    def _control(self, field: FormField) -> Locator:
        return field.native.locator(f'select[name="{field.name}"]')


class SplitDateTimeWidget:
    """The admin's date and time inputs of one date-time, read as the pair of texts they
    hold and filled from a ``datetime``, a ``(date, time)`` pair or ``None``."""

    def marker(self, field: FormField) -> str:
        # The admin draws the two inputs in a `p.datetime`, which a project's own widget
        # of two inputs doesn't.
        return f'p.datetime input[name="{field.name}_0"]'

    def read(self, field: FormField) -> tuple[str, str]:
        return self._input(field, 0).input_value(), self._input(field, 1).input_value()

    def fill(self, field: FormField, value: Any) -> None:
        date, time = self._texts(field, value)
        self._input(field, 0).fill(date)
        self._input(field, 1).fill(time)

    def _texts(self, field: FormField, value: Any) -> tuple[str, str]:
        """The date and the time to type for ``value``. Dates and times are typed in ISO
        format, which the admin accepts in any locale."""
        if value is None:
            return "", ""
        if isinstance(value, datetime.datetime):
            # The admin reads what is typed in the current time zone.
            if timezone.is_aware(value):
                value = timezone.localtime(value)
            return value.date().isoformat(), value.time().isoformat()
        if isinstance(value, (tuple, list)) and len(value) == 2:
            date, time = value
            # A datetime is also a date, but not one the date input takes.
            date_fits = _can_fill(date, datetime.date) and not isinstance(date, datetime.datetime)
            if date_fits and _can_fill(time, datetime.time):
                return _part_text(date), _part_text(time)
        raise TypeError(
            f"The field {field.name!r} takes a datetime, a (date, time) pair or None, "
            f"not {value!r}. Each half of the pair is a date or time, text, or None."
        )

    def _input(self, field: FormField, index: int) -> Locator:
        return field.native.locator(f'input[name="{field.name}_{index}"]')


class TextWidget:
    """Whatever one control carries the field's name, read and filled as text."""

    def marker(self, field: FormField) -> str:
        return f'[name="{field.name}"]'

    def read(self, field: FormField) -> str:
        return self._control(field).input_value()

    def fill(self, field: FormField, value: Any) -> None:
        self._control(field).fill("" if value is None else str(value))

    def _control(self, field: FormField) -> Locator:
        return field.native.locator(f'[name="{field.name}"]')


class Widgets:
    """The widget classes a form's fields are read and filled through, in the order
    they are tried: the ``custom`` ones, then the built-in ones.

    A built-in class is replaced by putting a custom class in front of it that
    recognizes the same control.
    """

    def __init__(self, custom: Iterable[Widget] = ()) -> None:
        # A text control is any control with the field's name, a checkbox and a select
        # included, so it comes last.
        self._widgets: tuple[Widget, ...] = (
            *custom,
            CheckboxWidget(),
            SelectWidget(),
            SplitDateTimeWidget(),
            TextWidget(),
        )

    def widget_for(self, field: FormField) -> Widget | None:
        """The first widget class whose marker matches inside the field's box, or
        ``None`` when none of them recognizes the field.

        Every marker is tried in one browser call, since each call costs a round trip
        whatever it asks.
        """
        index = field.native.evaluate(
            "(box, markers) => markers.findIndex(marker => box.querySelector(marker))",
            [_marker(widget, field) for widget in self._widgets],
        )
        return self._widgets[index] if index >= 0 else None


def _marker(widget: Widget, field: FormField) -> str:
    """The widget class's marker for the field, checked before the browser sees it."""
    marker = widget.marker(field)
    if not isinstance(marker, str) or not marker:
        raise TypeError(
            f"{type(widget).__name__}.marker() must return a non-empty CSS selector, "
            f"not {marker!r}."
        )
    return marker


def _option_spellings(value: Any) -> list[str]:
    """The option values ``value`` may be written as, in the order they are looked for.

    A select's options are the choice values as ``str()`` renders them, with ``""`` for
    the blank one. The exception is the widget Django gives a nullable boolean, whose
    three options are spelled ``"unknown"``, ``"true"`` and ``"false"``. Both spellings
    are Django's own and the page shows only which options it has, not which widget drew
    them, so a boolean is looked for under either.
    """
    if isinstance(value, FieldChoice):
        return [value.value]
    # A select of related objects offers each one by its primary key, which is what the
    # form posts for it.
    if isinstance(value, Model):
        return [str(value.pk)]
    # `is`, because `1 == True` and a number is no boolean here.
    if value is True:
        return ["True", "true"]
    if value is False:
        return ["False", "false"]
    if value is None:
        return ["", "unknown"]
    return [str(value)]


def _can_fill(value: Any, kind: type) -> bool:
    """Whether ``value`` can fill the input for a ``kind``: it's a ``kind``, text or ``None``."""
    return value is None or isinstance(value, (kind, str))


def _part_text(value: datetime.date | datetime.time | str | None) -> str:
    """What to type for one half of a date-time pair."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.isoformat()
