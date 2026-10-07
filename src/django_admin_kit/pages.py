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
from collections.abc import Mapping
from enum import Enum
from typing import Any, Dict
from urllib.parse import urlsplit

from django.apps import apps
from django.db.models import Model
from django.urls import Resolver404, resolve
from playwright.sync_api import Locator, Page, Response

from . import matching
from .errors import ValidationErrors
from .fields import Fields, FormField
from .messages import Messages
from .normalize import integer
from .rendered import text_of
from .results import SubmissionResult
from .rows import Row
from .urls import AdminUrls

_NOTHING = object()
"""What a source has for a field it says nothing about, which `None` cannot stand for."""


class PagePopulationMode(str, Enum):
    """Which of a form's fields ``FormPage.populate`` fills.

    A member is its own word, so ``PagePopulationMode.REQUIRED`` and ``"required"`` are
    the same thing to pass and the same thing to read in a failure.
    """

    REQUIRED = "required"
    OPTIONAL = "optional"
    ALL = "all"


class FormAction(str, Enum):
    """The actions the admin puts on every create and edit form, by the names they post.

    A member is the name itself, so it compares and hashes as that string and mixes with
    the name of an action a project adds: ``{FormAction.SAVE, "_approve"}``.
    """

    SAVE = "_save"
    SAVE_AND_CONTINUE = "_continue"
    SAVE_AND_ADD_ANOTHER = "_addanother"
    SAVE_AS_NEW = "_saveasnew"


class AdminPage:
    """One opened admin page."""

    # The page type the admin declares in the `body` class, or None for pages the
    # package does not model. The path and the status are usually enough to tell
    # whether the browser still shows this page. The class is needed when the admin
    # answers with a different page at the same URL and status 200: for example, a
    # project's `response_add` or `response_change` that renders a confirmation page
    # instead of redirecting, or, once changelist actions are supported, the
    # confirmation page of "Delete selected".
    _kind: str | None = None

    def __init__(self, page: Page, status_code: int, requested: str, urls: AdminUrls) -> None:
        self._page = page
        self._status_code = status_code
        self._requested = requested
        self._urls = urls
        self._landed()

    @property
    def native(self) -> Page:
        """The browser page, unwrapped, for anything the package does not model."""
        return self._page

    @property
    def status_code(self) -> int:
        """The status of the response the browser ended up on, after any redirects."""
        self._check()
        return self._status_code

    @property
    def destination(self) -> str:
        """The path the browser ended up on, comparable with ``admin_ui.url``.

        Query string and fragment are dropped, so a redirect to the login page compares
        equal to ``admin_ui.url.login()`` whatever ``next`` it carries.
        """
        self._check()
        return self._destination

    @property
    def redirected(self) -> bool:
        """Ended up somewhere other than the page asked for."""
        self._check()
        return self._redirected

    @property
    def works(self) -> bool:
        """Loaded where it was asked for."""
        self._check()
        return self._works

    @property
    def denied(self) -> bool:
        """Refused, whether by redirect to the login page or in place."""
        self._check()
        return self._status_code == 403 or self._destination == self._urls.login()

    @property
    def missing(self) -> bool:
        """Not there: a URL the admin does not serve, or an object that does not exist.

        The admin reports a missing object to a user with permission by redirecting
        to the index with a message, so a redirect there is read as missing. A user
        without permission is refused before the object is looked up. The one other
        page that redirects to the index is the login page, when the user is already
        logged in; that is a plain redirect.
        """
        self._check()
        if self._status_code == 404:
            return True
        return (
            self._redirected
            and self._destination == self._urls.index()
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

    @property
    def messages(self) -> Messages:
        """The messages the page shows, in order, each with its level and its text.

        Unlike everything else on a page, they are read even when the page did not open
        where it was asked. A missing object is the case in point: the admin sends the user
        to the index with a warning, and Django shows a message only once.
        """
        self._check()
        return Messages(self._message_items)

    @property
    def _destination(self) -> str:
        return urlsplit(self._page.url).path

    @property
    def _redirected(self) -> bool:
        return self._destination != self._requested

    @property
    def _works(self) -> bool:
        return self._status_code == 200 and not self._redirected

    def _shown(self) -> Page:
        """The page, once it is known to be the one that was asked for.

        A page that did not open shows nothing to read, and reading it anyway would
        let a test pass for a user who never saw it.
        """
        self._check()
        if not self._works:
            raise LookupError(
                "The page did not open, so there is nothing to read from it. "
                f"Status {self._status_code}, at {self._destination}."
            )
        return self._page

    def _message_items(self) -> Locator:
        # `_check` and not `_shown`: the messages of a page that did not open are where the
        # admin says why, so they are read from wherever the page landed. A page the browser
        # has left still fails, so held messages never read the next page's.
        self._check()
        return self._page.locator("ul.messagelist > li")

    def _landed(self) -> None:
        """Remember where the browser is now, as the page this object stands for.

        A page that did not open, such as one refused with a redirect to the login page,
        stands for wherever the browser landed, so it can still say how it was refused.
        """
        self._path = self._destination
        self._of_kind = _is_kind(self._page, self._kind)

    def _still_shown(self) -> bool:
        """Whether the browser still shows this page: the same path and, if the page was
        of its type, still that type."""
        if self._destination != self._path:
            return False
        return not self._of_kind or _is_kind(self._page, self._kind)

    def _check(self) -> None:
        """Fail at once if the browser has moved on to another page.

        Every reader runs this first, and so does every object the page hands out, so
        nothing reads a page the browser no longer shows.
        """
        if not self._still_shown():
            raise LookupError(
                f"The browser no longer shows this page; it is at {self._destination}. "
                "Read the page it shows now, such as a submission's result.page."
            )

    def _submitted(self, response: Response | None) -> SubmissionResult:
        """The result of a submission from this page, given the response it ended on."""
        # A navigation of the page always comes with a response.
        assert response is not None
        redirected = response.request.redirected_from is not None
        if self._still_shown():
            # The browser loaded a new document here, so report its status.
            self._status_code = response.status
            return SubmissionResult(self, redirected, self._urls)
        landed = _page_at(self._page, response.status, self._urls)
        return SubmissionResult(landed, redirected, self._urls)


class IndexPage(AdminPage):
    """The admin index: which models it lists for the current user."""

    _kind = "dashboard"

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

    @property
    def _app_list(self) -> dict[str, list[type]]:
        """App name to the registered models under it, as the page shows them."""
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

    _kind = "change-list"

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

    @property
    def rows(self) -> list[Row]:
        """The rows the changelist shows, in order.

        An empty changelist shows no table, so it has no rows either.
        """
        columns = self.columns
        elements = self._shown().locator("#result_list tbody tr").all()
        return [
            Row(element, index, columns, self._model, self._urls, self._check)
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

    @property
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

    @property
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


class FormPage(ModelPage):
    """An admin page with the model's form on it: which fields the form shows."""

    _kind = "change-form"

    @property
    def fields(self) -> Fields:
        """The fields the form shows, by name, in the order the admin presents them.

        A field the admin renders hidden is not shown to the user, so it is not here
        either; the browser posts it with the form all the same.
        """
        # The form's own fieldsets are direct children of the form's one div, which
        # leaves out the inline formsets next to them. Each line of a fieldset is a
        # `form-row` carrying a `field-<name>` class per field on it: a line with one
        # field is that field's box, a line with several holds a `fieldBox` per field.
        page = self._shown()
        # The admin says which language it rendered the page in, and the fields need
        # it to know what the form put after each label.
        language = page.locator("html").get_attribute("lang") or ""
        fields = Fields()
        for row in page.locator("form > div > fieldset.module .form-row").all():
            boxes = [row] if len(_field_names(row)) == 1 else row.locator(".fieldBox").all()
            for box in boxes:
                classes = (box.get_attribute("class") or "").split()
                if "hidden" in classes:
                    continue
                for name in _field_names(box):
                    fields[name] = FormField(box, name, language, self._check)
        return fields

    @property
    def required_fields(self) -> set[str]:
        """The names of the fields the form requires."""
        return {name for name, field in self.fields.items() if field.required}

    @property
    def optional_fields(self) -> set[str]:
        """The names of the fields the user may fill or leave alone.

        A field the user may only read is in neither set: there is nothing to fill.
        """
        return {
            name for name, field in self.fields.items() if field.editable and not field.required
        }

    @property
    def errors(self) -> ValidationErrors:
        """The validation errors the form shows; none until the admin rejects it."""
        self._shown()
        return ValidationErrors(
            lambda: self._shown().locator("#content-main form"), lambda: self.fields
        )

    @property
    def actions(self) -> set[str]:
        """The names of the actions the form offers: what each of its buttons posts.

        The names are the buttons' own, as the admin's view checks for them, so the admin's
        are ``"_save"`` and the like, also found in ``FormAction``, and a project's are what
        its template writes. A link submits nothing, so the delete link is not an action,
        and neither is the "Close" link shown to a user who may not save.
        """
        # A button without a name cannot be told apart by the view, so it is no action.
        buttons = self._submit_row.locator(
            'input[type="submit"][name], button[type="submit"][name], button:not([type])[name]'
        )
        return {str(button.get_attribute("name")) for button in buttons.all()}

    def has_action(self, name: str) -> bool:
        return name in self.actions

    @property
    def can_save(self) -> bool:
        return self.has_action(FormAction.SAVE)

    @property
    def can_save_and_continue(self) -> bool:
        return self.has_action(FormAction.SAVE_AND_CONTINUE)

    @property
    def can_save_and_add_another(self) -> bool:
        return self.has_action(FormAction.SAVE_AND_ADD_ANOTHER)

    @property
    def can_save_as_new(self) -> bool:
        return self.has_action(FormAction.SAVE_AS_NEW)

    @property
    def can_delete(self) -> bool:
        """Whether the form links to the page that deletes its object."""
        return self._submit_row.locator("a.deletelink").count() > 0

    @property
    def _submit_row(self) -> Locator:
        # An admin with `save_on_top` draws the same row above the form as well.
        return self._shown().locator("#content-main form .submit-row").first

    def populate(
        self,
        source: Any = None,
        mode: PagePopulationMode = PagePopulationMode.ALL,
        /,
        **values: Any,
    ) -> None:
        """Fill the form from ``source``, from ``values``, or from both.

        ``source`` is a dictionary read by field name, or any object read by attribute:
        a model instance, a namespace, or something the project wrote. A keyword adds a
        field the source lacks or overrides what it holds for one, so a test states the
        value it cares about next to the data it reuses. A field neither names is left
        as the page rendered it, and a name the form does not have fills nothing.

        ``mode`` narrows which fields are filled to the ones the form requires or to
        the ones it leaves to the user, so one set of data serves a test about either.
        Whatever the mode, the source is not checked against it: what it says about a
        field outside the mode is simply not used.

        The form decides what may be filled, not the source: the fields are filled in
        the order the form shows them, and a field the user may only read is passed
        over, as is one the admin renders hidden.
        """
        wanted = PagePopulationMode(mode)
        for name, field in self.fields.items():
            if not _within(wanted, field):
                continue
            value = values[name] if name in values else _value_of(source, name)
            if value is not _NOTHING:
                field.fill(value)

    def submit(self, action: str) -> SubmissionResult:
        """Click the button that posts ``action``, and wait for the next page.

        ``action`` is the button's ``name``, or a ``FormAction``. If the page has no such
        button, nothing is clicked and ``LookupError`` lists the actions it has.

        The result's page is this same object if the browser stayed on this page, for
        example when the admin rejects the form and shows it again.
        """
        # Use the plain name, so an error shows "_save" rather than the enum member.
        name = action.value if isinstance(action, FormAction) else action
        # Read the actions once, for both the check and the error message.
        offered = self.actions
        if name not in offered:
            raise LookupError(
                f"The page offers no action {name!r}. Actions: "
                f"{', '.join(repr(each) for each in sorted(offered)) or 'none'}."
            )
        with self._page.expect_navigation() as navigation:
            self._submit_row.locator(f'[name="{name}"]').first.click()
        return self._submitted(navigation.value)

    def save(self) -> SubmissionResult:
        return self.submit(FormAction.SAVE)

    def save_and_continue(self) -> SubmissionResult:
        return self.submit(FormAction.SAVE_AND_CONTINUE)

    def save_and_add_another(self) -> SubmissionResult:
        return self.submit(FormAction.SAVE_AND_ADD_ANOTHER)


class CreatePage(FormPage):
    """The page that adds a new instance of a model."""


class EditPage(FormPage):
    """The change page of one instance, read only for a user who may only view it."""

    # Both of these need an object that already exists, so the admin offers them on an
    # edit page and never on a create page.
    def save_as_new(self) -> SubmissionResult:
        return self.submit(FormAction.SAVE_AS_NEW)

    def delete(self) -> DeletePage:
        """Follow the delete link to the page that asks to confirm the deletion.

        Deleting takes two steps in the admin, and this is the first: nothing is deleted
        until ``confirm_deleting`` on the returned page. The link submits nothing, so the
        confirmation page comes back on its own, as opening it directly would give it. If
        the page has no delete link, nothing is clicked and ``LookupError`` says so.
        """
        link = self._submit_row.locator("a.deletelink")
        if not link.count():
            raise LookupError("The page offers no delete link.")
        # The link may carry the changelist's filters in its query; the page is its path.
        path = urlsplit(link.get_attribute("href") or "").path
        with self._page.expect_navigation() as navigation:
            link.click()
        response = navigation.value
        # A navigation of the page always comes with a response.
        assert response is not None
        return DeletePage(self._page, response.status, path, self._urls, self._model)


class DeletePage(ModelPage):
    """The page that asks whether to delete one instance."""

    _kind = "delete-confirmation"

    @property
    def can_confirm_deleting(self) -> bool:
        """Whether the page lets the user confirm the deletion.

        The admin offers no confirmation when deleting the object would also delete
        objects that are protected, or that the user may not delete; the page then lists
        them instead.
        """
        return self._confirm_button.count() > 0

    @property
    def deletions(self) -> list[str]:
        """What the deletion will remove, as the page lists it: the object itself, then every
        related object it takes with it, in the order shown.

        Each entry is the text the page shows, such as ``"Product: Widget"``, whether or not
        the admin links it. The page draws the list nested; it is read top to bottom. A page
        that cannot be confirmed removes nothing, so it has none. On Django 6.1, an admin
        that sets ``delete_confirmation_max_display`` shows only part of the list, ending in
        an entry such as "…and 2 more objects.", which is read as shown too.
        """
        # The list of what is removed follows its heading, which follows the summary's list.
        # The lists a page shows when it cannot be confirmed follow the opening sentence,
        # and before Django 4.2 none of the lists has an id to tell them apart.
        items = self._shown().locator("#content > ul + h2 + ul li").all()
        return [_own_text(item) for item in items]

    @property
    def deletion_counts(self) -> DeletionCounts:
        """How many objects of each model the deletion will remove, as the page's "Summary"
        counts them, such as ``{"Products": 1, "Reviews": 2}``.

        The keys are the labels the page shows, in the order shown; the page names a model by
        nothing else. A model the deletion removes none of is not counted, so it is not a key.
        A page that cannot be confirmed removes nothing, so it counts nothing. The counts stay
        whole when Django 6.1 shows only part of the deletions.
        """
        # The summary's list follows its heading, which follows the opening sentence. A page
        # that cannot be confirmed has a list right after the sentence, and no heading.
        counts = DeletionCounts()
        for item in self._shown().locator("#content > p + h2 + ul > li").all():
            label, _, count = text_of(item).rpartition(": ")
            counts[label] = integer(count)
        return counts

    def confirm_deleting(self) -> SubmissionResult:
        """Click "Yes, I'm sure", and wait for the next page.

        If the page offers no confirmation, nothing is clicked and ``LookupError`` says
        so.
        """
        button = self._confirm_button
        if not button.count():
            raise LookupError("The page offers no way to confirm the deletion.")
        with self._page.expect_navigation() as navigation:
            button.click()
        return self._submitted(navigation.value)

    @property
    def _confirm_button(self) -> Locator:
        return self._shown().locator('#content form input[type="submit"]')


class DeletionCounts(Dict[str, int]):
    """How many objects of each model a deletion removes, by the label the page shows.

    A plain dict, so membership, ``set()`` and ``list()`` are what they always are; only a
    miss says more than a bare ``KeyError`` would.
    """

    def __missing__(self, key: str) -> int:
        raise KeyError(
            f"The page counts no model {key!r}. Models: "
            f"{', '.join(repr(label) for label in self) or 'none'}."
        )


# The page class for each admin view of a model, by the end of the view's URL name.
_MODEL_PAGES: dict[str, type[ModelPage]] = {
    "changelist": ChangelistPage,
    "add": CreatePage,
    "change": EditPage,
    "delete": DeletePage,
}


def _page_at(page: Page, status_code: int, urls: AdminUrls) -> AdminPage:
    """A page object for the page the browser is on.

    The class comes from the URL, and is used only if the page's ``body`` class confirms
    it; otherwise the result is a plain ``AdminPage``. The page counts as requested at its
    current path, so it reads like a page the test opened directly.
    """
    path = urlsplit(page.url).path
    try:
        match = resolve(path)
    except Resolver404:
        return AdminPage(page, status_code, path, urls)
    # A view added to the admin without a name has no URL name.
    url_name = match.url_name or ""
    if match.namespace != urls.site.name:
        return AdminPage(page, status_code, path, urls)
    # A view can render a different page at its own URL, so the URL alone is not trusted.
    if url_name == "index" and _is_kind(page, IndexPage._kind):
        return IndexPage(page, status_code, path, urls)
    # Find the model by the full prefix of its URL names, such as "shop_product_",
    # because an app label may itself contain underscores.
    for model in apps.get_models():
        if not urls.site.is_registered(model):
            continue
        prefix = f"{model._meta.app_label}_{model._meta.model_name}_"
        if url_name.startswith(prefix):
            page_class = _MODEL_PAGES.get(url_name[len(prefix) :])
            if page_class is not None and _is_kind(page, page_class._kind):
                return page_class(page, status_code, path, urls, model)
    return AdminPage(page, status_code, path, urls)


def _is_kind(page: Page, kind: str | None) -> bool:
    """Whether ``page`` has the page type ``kind`` in its ``body`` class. ``None``
    matches any page."""
    if kind is None:
        return True
    return kind in (page.locator("body").get_attribute("class") or "").split()


def _within(mode: PagePopulationMode, field: FormField) -> bool:
    """Whether ``mode`` covers ``field``, which must have something to fill at all."""
    if not field.editable:
        return False
    if mode is PagePopulationMode.REQUIRED:
        return field.required
    if mode is PagePopulationMode.OPTIONAL:
        return not field.required
    return True


def _value_of(source: Any, name: str) -> Any:
    """What ``source`` holds for the field named ``name``, or ``_NOTHING``.

    A dictionary is read by key and anything else by attribute, so a model instance, a
    namespace and a project's own object are all sources, and only the form's own field
    names are ever asked for.
    """
    if source is None:
        return _NOTHING
    if isinstance(source, Mapping):
        return source.get(name, _NOTHING)
    return getattr(source, name, _NOTHING)


def _text(element: Locator) -> str:
    return (element.text_content() or "").strip() if element.count() else ""


def _own_text(item: Locator) -> str:
    """The text of a list entry without the entries nested in it, whitespace collapsed."""
    text = item.evaluate(
        "el => Array.from(el.childNodes)"
        ".filter(node => node.nodeName !== 'UL')"
        ".map(node => node.textContent).join('')"
    )
    return " ".join(str(text).split())


def _token(element: Locator, prefix: str) -> str:
    classes = (element.get_attribute("class") or "").split()
    return next(c[len(prefix) :] for c in classes if c.startswith(prefix))


def _field_names(element: Locator) -> list[str]:
    # A field's box carries one `field-<name>` class; a line with several fields
    # carries all of theirs. For example, class="form-row field-sku field-price".
    classes = (element.get_attribute("class") or "").split()
    return [c[len("field-") :] for c in classes if c.startswith("field-")]
