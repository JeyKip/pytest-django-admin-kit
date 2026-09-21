"""The fields of an admin form, as the page shows them.

A field is addressed by its name, never by the label shown next to it. Its element is
the box the admin draws around label, control and help text, which is the one thing
every field has whether the user may fill it or only read it.
"""

from __future__ import annotations

from functools import cached_property
from typing import Any, Dict

from django.utils import translation
from playwright.sync_api import Locator

from .rendered import RenderedValue, text_of


class FieldChoice:
    """One option a field offers: its ``value``, what the form posts, and its ``label``,
    what the user reads.

    A choice compares equal to another choice and to a ``(value, label)`` pair, as a
    tuple or a list, and to nothing else. A bare string is neither part, so a test
    says which one it means: ``field.value.label == "Tools"``.
    """

    def __init__(self, value: str, label: str) -> None:
        self._value = value
        self._label = label

    @property
    def value(self) -> str:
        return self._value

    @property
    def label(self) -> str:
        return self._label

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FieldChoice):
            return (self._value, self._label) == (other._value, other._label)
        if isinstance(other, (tuple, list)) and len(other) == 2:
            return (self._value, self._label) == tuple(other)
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self._value, self._label))

    def __repr__(self) -> str:
        return f"FieldChoice({self._value!r}, {self._label!r})"


class FormField:
    """One field of an admin form.

    ``language`` is the one the page was rendered in, which decides what the admin put
    after the label.
    """

    def __init__(self, element: Locator, name: str, language: str) -> None:
        self._element = element
        self._name = name
        self._language = language

    @property
    def name(self) -> str:
        """The name the form knows the field by."""
        return self._name

    @property
    def native(self) -> Locator:
        """The field's box, unwrapped, for anything the package does not model."""
        return self._element

    @cached_property
    def required(self) -> bool:
        """Whether the form requires a value, as the admin tells the user.

        The admin marks a required field on its label, from the form field as the form
        finally has it, so a ``ModelForm`` that changes what the model says is read the
        way the user sees it. A field the user may only read is never required.
        """
        return "required" in (self._label.get_attribute("class") or "").split()

    @cached_property
    def label(self) -> str:
        """The label the admin shows next to the field, as data and never as an address.

        The suffix the form puts after every label, ``:`` in English and whatever the
        page's language makes of it, is not part of the label and is taken off.
        """
        label = text_of(self._label)
        # The suffix is Django's own translated ":", so the catalog says what the page
        # ends each label with: "Name:" in English, "Name\xa0:" in French, a full-width
        # colon in Traditional Chinese. It is looked up in the page's language, not the
        # test's: a project that picks the language per request renders the page in
        # one while the test thread is in another. Collapsing the suffix as the label
        # was collapsed turns the French "\xa0:" into ":", so "Name :" ends with it
        # and the space left over is dropped too.
        with translation.override(self._language):
            suffix = " ".join(translation.gettext(":").split())
        return label[: -len(suffix)].rstrip() if label.endswith(suffix) else label

    @cached_property
    def editable(self) -> bool:
        """Whether the field has a control to fill, rather than a value to read."""
        return self._element.locator("div.readonly").count() == 0

    @property
    def value(self) -> Any:
        """What the field holds right now, as the user reads it.

        A control holds its text: a checkbox reads as ``True`` or ``False``, a select as
        the ``FieldChoice`` chosen, anything else as the text typed into it. A field the
        user may only read is read as a changelist cell is: its text, or the boolean
        the admin drew as an icon.
        """
        if not self.editable:
            return self._rendered.value
        # Each kind of control is asked for by name and by what it is. A widget that
        # renders several controls under the name, such as a group of radio buttons,
        # is not read yet.
        if (checkbox := self._control('input[type="checkbox"]')).count():
            return checkbox.is_checked()
        if (select := self._control("select")).count():
            option = select.locator("option:checked")
            return FieldChoice(option.get_attribute("value") or "", text_of(option))
        return self._control("").input_value()

    def _control(self, kind: str) -> Locator:
        return self._element.locator(f'{kind}[name="{self._name}"]')

    @cached_property
    def _label(self) -> Locator:
        # Django labels most fields with `label` and, from 6.0, a widget that groups
        # several inputs with `legend`.
        return self._element.locator("label, legend").first

    @cached_property
    def _rendered(self) -> RenderedValue:
        return RenderedValue(self._element.locator("div.readonly"))

    def __repr__(self) -> str:
        return f"FormField({self._name!r})"


class Fields(Dict[str, FormField]):
    """The fields of a form by name, in the order the admin presents them.

    A plain dict, so membership, ``set()`` and ``list()`` are what they always are;
    only a miss says more than a bare ``KeyError`` would.
    """

    def __missing__(self, key: str) -> FormField:
        raise KeyError(
            f"The form has no field named {key!r}. Fields: "
            f"{', '.join(repr(name) for name in self)}."
        )
