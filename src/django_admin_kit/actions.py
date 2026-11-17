"""The actions a changelist offers in its action bar, by name.

The bar lists them in a select whose options send the action's name and show its description,
which is translated and follows the model's verbose name. So an action is addressed by its name
and its description is read as data. An admin can draw the bar above the table and below it;
both list the same actions, so the first is read.
"""

from __future__ import annotations

from typing import Callable, Iterator, Mapping

from playwright.sync_api import Locator, Page

from ._html import stripped_text


class ChangelistAction:
    """One action a changelist offers, read from its option each time it is used."""

    def __init__(self, name: str, shown: Callable[[], Page]) -> None:
        self._name = name
        self._shown = shown

    @property
    def name(self) -> str:
        """The name the admin registers the action under, as ``page.actions`` lists it."""
        return self._name

    @property
    def label(self) -> str:
        """The description the action bar shows for the action."""
        return stripped_text(self.native)

    @property
    def native(self) -> Locator:
        """The action's ``option`` in the action bar, unwrapped, for anything the package does
        not model."""
        option = _options(self._shown(), f'[value="{self._name}"]')
        if not option.count():
            raise LookupError(f"The changelist no longer offers the action {self._name!r}.")
        return option

    def __repr__(self) -> str:
        return f"ChangelistAction({self._name!r})"


class ChangelistActions(Mapping[str, ChangelistAction]):
    """The actions a changelist offers, by name, in the order its action bar lists them.

    A read-only mapping that reads the page each time it is used, as each action does. It is
    empty when the page draws no action bar. A miss lists the names there are. ``shown`` gives
    the page once it is known to be the changelist the actions are on.
    """

    def __init__(self, shown: Callable[[], Page]) -> None:
        self._shown = shown

    def __getitem__(self, key: str) -> ChangelistAction:
        names = self._names()
        if key not in names:
            listed = (
                "Actions: " + ", ".join(repr(name) for name in names)
                if names
                else "The changelist offers no actions"
            )
            raise KeyError(f"No action named {key!r} here. {listed}.")
        return ChangelistAction(key, self._shown)

    def __iter__(self) -> Iterator[str]:
        return iter(self._names())

    def __len__(self) -> int:
        return len(self._names())

    def __repr__(self) -> str:
        return f"ChangelistActions({self._names()!r})"

    def _names(self) -> list[str]:
        return [name for name in _names(_options(self._shown())) if name]


def _options(page: Page, which: str = "") -> Locator:
    """The options of the page's first action bar, the blank "---------" among them, or only
    those ``which`` selects, such as ``'[value="delete_selected"]'``."""
    return page.locator('div.actions select[name="action"]').first.locator(f"option{which}")


def _names(options: Locator) -> list[str]:
    """The values of the action bar's options, in order, the blank one's ``""`` included."""
    names: list[str] = options.evaluate_all("options => options.map(option => option.value)")
    return names
