"""The actions a changelist offers in its action bar, by name.

The bar lists them in a select whose options send the action's name and show its description,
which is translated and follows the model's verbose name. So an action is addressed by its name
and its description is read as data. An admin can draw the bar above the table and below it;
both list the same actions, so the first is read.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Iterator, Mapping

from playwright.sync_api import Locator, Page

from ._html import stripped_text

if TYPE_CHECKING:
    from .pages import AdminPage


class ChangelistAction:
    """One action a changelist offers, read from its option each time it is used."""

    def __init__(
        self, name: str, shown: Callable[[], Page], run: Callable[[str], AdminPage]
    ) -> None:
        self._name = name
        self._shown = shown
        self._run = run

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
        return self._option()

    def run(self) -> AdminPage:
        """Choose the action in the action bar, click the bar's button, and return the page
        the browser shows after it.

        The action runs on the rows selected. Django runs none with nothing selected: it sends
        the browser back to the changelist with a warning, which ``page.messages`` reads. When
        the admin comes back to the changelist, as it does after an action of its own, the page
        returned is this same changelist object, which then reads the page loaded again.
        Otherwise it is a new page object for wherever the action led, such as the change page
        an action redirects to, or the login page, which reads as ``denied``, after the session
        ended. An action the changelist no longer offers raises ``LookupError``, and nothing is
        clicked.
        """
        # Only for its LookupError, so nothing is clicked for an action that is gone.
        self._option()
        return self._run(self._name)

    def __repr__(self) -> str:
        return f"ChangelistAction({self._name!r})"

    def _option(self) -> Locator:
        option = _options(self._shown(), f'[value="{self._name}"]')
        if not option.count():
            raise LookupError(f"The changelist no longer offers the action {self._name!r}.")
        return option


class ChangelistActions(Mapping[str, ChangelistAction]):
    """The actions a changelist offers, by name, in the order its action bar lists them.

    A read-only mapping that reads the page each time it is used, as each action does. It is
    empty when the page draws no action bar. A miss lists the names there are. ``shown`` gives
    the page once it is known to be the changelist the actions are on, and ``run`` runs an
    action by its name and returns the page the browser shows after it.
    """

    def __init__(self, shown: Callable[[], Page], run: Callable[[str], AdminPage]) -> None:
        self._shown = shown
        self._run = run

    def __getitem__(self, key: str) -> ChangelistAction:
        names = self._names()
        if key not in names:
            listed = (
                "Actions: " + ", ".join(repr(name) for name in names)
                if names
                else "The changelist offers no actions"
            )
            raise KeyError(f"No action named {key!r} here. {listed}.")
        return ChangelistAction(key, self._shown, self._run)

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
