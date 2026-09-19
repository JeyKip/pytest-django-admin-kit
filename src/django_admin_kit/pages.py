"""Admin pages after they have been opened: where the browser ended up, and whether
it got in.

The admin answers a page request in more ways than a status code shows. A user who
is not logged in or not staff is redirected to the login page. A staff user without
permission for a model is refused in place with a 403. A user who has permission but
asks for an object that does not exist is sent to the index with a message, and a
URL the admin does not serve is a 404. One resolver turns the requested path, the
final path and the status into ``works``, ``denied``, ``missing`` and ``redirected``,
so that reading is written once.
"""

from __future__ import annotations

import re
from functools import cached_property
from typing import Any
from urllib.parse import urlsplit

from django.apps import apps
from django.db.models import Model
from playwright.sync_api import Locator, Page

from . import matching
from .normalize import integer
from .rows import Row
from .urls import AdminUrls


class AdminPage:
    """One opened admin page."""

    def __init__(self, page: Page, status_code: int, requested: str, urls: AdminUrls) -> None:
        self._page = page
        self._status_code = status_code
        self._requested = requested
        self._urls = urls

    @property
    def native(self) -> Page:
        """The browser page, unwrapped, for anything the package does not model."""
        return self._page

    @property
    def status_code(self) -> int:
        """The status of the response the browser ended up on, after any redirects."""
        return self._status_code

    @property
    def destination(self) -> str:
        """The path the browser ended up on, comparable with ``admin_ui.url``.

        Query string and fragment are dropped, so a redirect to the login page compares
        equal to ``admin_ui.url.login()`` whatever ``next`` it carries.
        """
        return urlsplit(self._page.url).path

    @property
    def redirected(self) -> bool:
        """Ended up somewhere other than the page asked for."""
        return self.destination != self._requested

    @property
    def works(self) -> bool:
        """Loaded where it was asked for."""
        return self._status_code == 200 and not self.redirected

    @property
    def denied(self) -> bool:
        """Refused, whether by redirect to the login page or in place."""
        return self._status_code == 403 or self.destination == self._urls.login()

    @property
    def missing(self) -> bool:
        """Not there: a URL the admin does not serve, or an object that does not exist.

        The admin reports a missing object to a user with permission by redirecting
        to the index with a message, so a redirect there is read as missing. A user
        without permission is refused before the object is looked up. The one other
        page that redirects to the index is the login page, when the user is already
        logged in; that is a plain redirect.
        """
        if self._status_code == 404:
            return True
        return (
            self.redirected
            and self.destination == self._urls.index()
            and self._requested != self._urls.login()
        )

    @property
    def title(self) -> str:
        """The title the admin renders for the page, or ``""`` when it renders none."""
        return _text(self._shown().locator("#content h1").first)

    @property
    def subtitle(self) -> str:
        """The subtitle under the title, such as the object's name on a change page."""
        # The subtitle is the heading right after the title. The content area holds
        # other h2 elements, for filters and the like, but none next to the h1.
        return _text(self._shown().locator("#content h1 + h2"))

    def _shown(self) -> Page:
        """The page, once it is known to be the one that was asked for.

        A page that did not open shows nothing to read, and reading it anyway would
        let a test pass for a user who never saw it.
        """
        if not self.works:
            raise LookupError(
                "The page did not open, so there is nothing to read from it. "
                f"Status {self.status_code}, at {self.destination}."
            )
        return self._page


class IndexPage(AdminPage):
    """The admin index: which models it lists for the current user."""

    @property
    def apps(self) -> list[str]:
        """The apps the index shows, by the name shown, in the order shown.

        An app is shown only when the user may see at least one of its models.
        """
        return list(self._app_list)

    @property
    def models(self) -> list[type]:
        """The registered models the index shows, in the order shown.

        A model the user may not see is not on the page, so it is not here either.
        """
        return [model for models in self._app_list.values() for model in models]

    def models_for(self, app: str) -> list[type]:
        """The models the index shows under one app, named as ``apps`` names it."""
        try:
            return list(self._app_list[app])
        except KeyError:
            raise LookupError(
                f"The index shows no app named {app!r}. Shown: "
                f"{', '.join(repr(name) for name in self._app_list) or 'none'}."
            ) from None

    @cached_property
    def _app_list(self) -> dict[str, list[type]]:
        """App name to the registered models under it, read from the page once."""
        # Django renders the app list twice, the second time in the navigation
        # sidebar, so reading stays inside the content area. Each app is a `module`
        # block with an `app-<label>` class; each model a row with `model-<name>`,
        # which also leaves out the header row newer Django versions add. The names
        # are read from the class list rather than by a substring match because
        # Django 6.1 puts a class named `app-list` on the content area itself.
        app_list: dict[str, list[type]] = {}
        for app in self._shown().locator("#content-main div.module").all():
            # `text_content`, not `inner_text`: the admin's stylesheet upper-cases
            # captions, and the name is what the document says, not how it is drawn.
            name = _text(app.locator("caption"))
            app_label = _token(app, "app-")
            app_list[name] = [
                model
                for row in app.locator("tr[class*='model-']").all()
                if (model := self._registered_model(app_label, row)) is not None
            ]
        return app_list

    def _registered_model(self, app_label: str, row: Locator) -> type | None:
        # Matching the registry rather than the changelist link finds a model the
        # user may only add, which the admin lists without a link. A row that is no
        # registered model, which a third-party app may add, is left out.
        try:
            model = apps.get_model(app_label, _token(row, "model-"))
        except LookupError:
            return None
        return model if self._urls.site.is_registered(model) else None


class ModelPage(AdminPage):
    """An admin page about one model, which it keeps for what reads it."""

    def __init__(
        self, page: Page, status_code: int, requested: str, urls: AdminUrls, model: type[Model]
    ) -> None:
        super().__init__(page, status_code, requested, urls)
        self._model = model


class ChangelistPage(ModelPage):
    """A model's changelist: its columns, its rows, and how many records it reports."""

    @property
    def headers(self) -> list[str]:
        """The column labels the page shows, in order.

        An empty changelist shows no table, so it has no headers either.
        """
        return [_text(cell.locator("div.text")) for cell in self._header_cells]

    def has_header(self, label: str) -> bool:
        return label in self.headers

    @property
    def columns(self) -> list[str]:
        """The same columns by the names the admin is configured with, in the same order."""
        return [_token(cell, "column-") for cell in self._header_cells]

    def has_column(self, name: str) -> bool:
        return name in self.columns

    @cached_property
    def rows(self) -> list[Row]:
        """The rows the changelist shows, in order.

        An empty changelist shows no table, so it has no rows either.
        """
        columns = self.columns
        elements = self._shown().locator("#result_list tbody tr").all()
        return [
            Row(element, index, columns, self._model, self._urls)
            for index, element in enumerate(elements)
        ]

    def contains(self, pattern: Any) -> bool:
        """Whether some row matches ``pattern``, a cell pattern per column in order,
        or ``ANY_ROW``.

        Returns ``True``; when no row matches, raises ``AssertionError`` showing the
        pattern and every row the changelist has.
        """
        __tracebackhide__ = True
        return matching.contains(pattern, self.rows)

    def match(self, patterns: Any) -> bool:
        """Whether the changelist is exactly ``patterns``: as many rows as patterns, in a
        list or tuple, each row matching the pattern at its position; ``ANY_ROW`` holds
        a position.

        Returns ``True``; otherwise raises ``AssertionError`` showing the patterns, what
        went wrong and every row the changelist has.
        """
        __tracebackhide__ = True
        return matching.match(patterns, self.rows)

    @cached_property
    def _header_cells(self) -> list[Locator]:
        # The checkbox Django adds for actions is a column only for users who have an
        # action to run, and it has no label, so it is not one here. The label is read
        # from `div.text` because the cell also holds sorting controls.
        return self._shown().locator("#result_list thead th:not(.action-checkbox-column)").all()

    @property
    def count(self) -> int:
        """The number of records the changelist reports, across all of its pages."""
        return integer(self._count_line.group("number"))

    @property
    def summary(self) -> str:
        """The count as the page words it, such as ``"3 products"``."""
        return self._count_line.group(0)

    @property
    def empty(self) -> bool:
        """Reports no records at all."""
        return self.count == 0

    @cached_property
    def _count_line(self) -> re.Match[str]:
        # The count is the paginator's own text. Page links, "Show all" and, from
        # Django 6.0, a heading for screen readers are all inside child elements, so
        # only the element's direct text nodes are read.
        paginator = self._shown().locator("#changelist .paginator")
        text = paginator.evaluate(
            "el => Array.from(el.childNodes)"
            ".filter(node => node.nodeType === Node.TEXT_NODE)"
            ".map(node => node.textContent).join(' ')"
        )
        # The number may carry grouping characters when the project localizes it,
        # which is why the name is required to start with something other than a
        # digit.
        match = re.search(r"(?P<number>\d[\d,.\s]*?)\s+[^\d\s].*", " ".join(str(text).split()))
        assert match is not None, f"unexpected paginator text {text!r}"
        return match


class CreatePage(ModelPage):
    """The page that adds a new instance of a model."""


class EditPage(ModelPage):
    """The change page of one instance, read only for a user who may only view it."""


class DeletePage(ModelPage):
    """The page that asks whether to delete one instance."""


def _text(element: Locator) -> str:
    return (element.text_content() or "").strip() if element.count() else ""


def _token(element: Locator, prefix: str) -> str:
    classes = (element.get_attribute("class") or "").split()
    return next(c[len(prefix) :] for c in classes if c.startswith(prefix))
