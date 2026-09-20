"""The fields of an admin form, as the page shows them.

A field is addressed by its name, never by the label shown next to it. Its element is
the box the admin draws around label, control and help text, which is the one thing
every field has whether the user may fill it or only read it.
"""

from __future__ import annotations

from functools import cached_property
from typing import Dict

from playwright.sync_api import Locator


class FormField:
    """One field of an admin form."""

    def __init__(self, element: Locator, name: str) -> None:
        self._element = element
        self._name = name

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
        # Django labels most fields with `label` and, from 6.0, a widget that groups
        # several inputs with `legend`; either carries the `required` class.
        label = self._element.locator("label, legend").first
        return "required" in (label.get_attribute("class") or "").split()

    @cached_property
    def editable(self) -> bool:
        """Whether the field has a control to fill, rather than a value to read."""
        return self._element.locator("div.readonly").count() == 0

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
