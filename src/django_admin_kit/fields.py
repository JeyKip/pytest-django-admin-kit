"""The fields of an admin form, as the page shows them.

A field is addressed by its name, never by the label shown next to it. Its element is
the box the admin draws around label, control and help text, which is the one thing
every field has whether the user may fill it or only read it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict

from django.contrib.admin import ModelAdmin
from django.utils import translation
from playwright.sync_api import Locator

from .normalize import Normalizers
from .rendered import Link, RenderedValue, text_of

if TYPE_CHECKING:
    from .widgets import Widgets


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
    after the label. ``check`` is run before every read, and fails when the browser no
    longer shows the page the field is on. ``normalizers`` read the value of a field the
    user may only read, by what stands behind it on the page ``model_admin`` draws, and
    ``widgets`` read and fill the field's control.
    """

    def __init__(
        self,
        element: Locator,
        name: str,
        language: str,
        check: Callable[[], None],
        normalizers: Normalizers,
        model_admin: ModelAdmin,
        widgets: Widgets,
    ) -> None:
        self._element = element
        self._name = name
        self._language = language
        self._check = check
        self._normalizers = normalizers
        self._model_admin = model_admin
        self._widgets = widgets

    @property
    def name(self) -> str:
        """The name the form knows the field by."""
        return self._name

    @property
    def native(self) -> Locator:
        """The field's box, unwrapped, for anything the package does not model."""
        return self._element

    @property
    def required(self) -> bool:
        """Whether the form requires a value, as the admin tells the user.

        The admin marks a required field on its label, from the form field as the form
        finally has it, so a ``ModelForm`` that changes what the model says is read the
        way the user sees it. A field the user may only read is never required.
        """
        self._check()
        return "required" in (self._label.get_attribute("class") or "").split()

    @property
    def label(self) -> str:
        """The label the admin shows next to the field, as data and never as an address.

        The suffix the form puts after every label, ``:`` in English and whatever the
        page's language makes of it, is not part of the label and is taken off.
        """
        self._check()
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

    @property
    def editable(self) -> bool:
        """Whether the field has a control to fill, rather than a value to read."""
        self._check()
        return self._element.locator("div.readonly").count() == 0

    @property
    def value(self) -> Any:
        """What the field holds right now, as the user reads it.

        A control is read by its widget class: a checkbox reads as ``True`` or
        ``False``, a select as the ``FieldChoice`` chosen, anything else as the text
        typed into it. A field the user may only read is read as a changelist cell is:
        its text, or the boolean the admin drew as an icon.
        """
        self._check()
        if not self.editable:
            return self._rendered.value
        return self._widgets.widget_for(self).read(self)

    @property
    def links(self) -> list[Link]:
        """The links in a rendered-only field's value, in order, like ``Cell.links``.

        ``[]`` for an editable field: its value is what the control holds, and the
        icons the admin may draw next to a select are not part of it.
        """
        self._check()
        return [] if self.editable else self._rendered.links

    @property
    def errors(self) -> list[str]:
        """The errors the admin shows for the field, in order; ``[]`` when it shows none.

        A field can fail several rules at once, so this is always a list.
        """
        self._check()
        items = self._element.locator("ul.errorlist > li").all()
        # A field that shares its line with others has a box of its own. Django 4.2 to 6.0
        # put its errors next to that box, in a wrapper around the two; the others put
        # them inside it. The wrapper holds one field, so its list is this field's.
        if "fieldBox" in (self._element.get_attribute("class") or "").split():
            wrapper = self._element.locator("xpath=..")
            items = wrapper.locator(":scope > ul.errorlist > li").all() + items
        return [text_of(item) for item in items]

    def fill(self, value: Any) -> None:
        """Put ``value`` into the field, the way a user would.

        The field's widget class fills it: a checkbox is checked or cleared by the
        value's truth, a select is given the option that stands for the value, and every
        other control is filled with the value's text, ``None`` emptying it. A field the
        user may only read has nothing to fill.
        """
        self._check()
        if not self.editable:
            raise LookupError(
                f"The field {self._name!r} is rendered only, so there is nothing to fill."
            )
        self._widgets.widget_for(self).fill(self, value)

    @property
    def choices(self) -> list[FieldChoice]:
        """The options a select offers, in order, the blank one included.

        ``[]`` for any other field: a text input has no fixed set of options, and a
        field the user may only read offers none.
        """
        self._check()
        if not self.editable:
            return []
        choices = getattr(self._widgets.widget_for(self), "choices", None)
        return [] if choices is None else choices(self)

    @property
    def _label(self) -> Locator:
        # Django labels most fields with `label` and, from 6.0, a widget that groups
        # several inputs with `legend`.
        return self._element.locator("label, legend").first

    @property
    def _rendered(self) -> RenderedValue:
        return RenderedValue(
            self._element.locator("div.readonly"),
            self._check,
            self._normalizers,
            self._model_admin,
            self._name,
        )

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
