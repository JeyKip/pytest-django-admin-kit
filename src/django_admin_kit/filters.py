"""The filters a changelist offers in its sidebar, grouped by the field they filter.

The page never says which ``list_filter`` entry a filter came from, and its title is the
field's verbose name, which repeats and is translated. What a filter does say is which URL
parameters its links send, so a filter is named after those, reduced to the field.
"""

from __future__ import annotations

import re
from typing import Callable, Iterable, Iterator, Mapping, Sequence, overload
from urllib.parse import parse_qs, urlsplit

from django.contrib.admin.utils import NotRelationField, get_fields_from_path
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Field, Model
from playwright.sync_api import Locator, Page

# The admin's "Clear all filters": the one link in the sidebar outside every filter's list that
# isn't "Show counts" or "Hide counts". Its text is translated, and its id is gone from 5.0.
_CLEAR_ALL = "#changelist-filter a:not(ul a):not(.viewlink):not(.hidelink)"


class FieldFilter:
    """One filter in the sidebar: the one at its position among its field's filters, read
    each time it is used."""

    def __init__(self, group: FieldFilters, index: int) -> None:
        self._group = group
        self._index = index

    @property
    def native(self) -> Locator:
        """The filter's ``ul`` of links, unwrapped, for anything the package does not model."""
        return self._located()[0]

    @property
    def choices(self) -> list[str]:
        """The labels of the filter's choices, in order, as the page shows them, with counts
        when it shows those."""
        return _choices(self.native)

    @property
    def selected(self) -> str | None:
        """The label of the choice the page marks selected, or ``None`` when it marks none.

        Django marks none on a date filter while another filter on the same field is applied,
        since the date filter compares every parameter of the field with its links.
        """
        return _selected(self.native)

    def apply(self, choice: str) -> None:
        """Click the link of ``choice`` and wait for the page it leads to.

        ``choice`` is a label as ``choices`` reads it, or the same label without its count, so
        ``"Yes"`` also applies "Yes (3)". This same page then reads the results. The admin's link
        keeps what else is applied, such as a search or another filter. A label the filter
        doesn't offer, or offers more than once, raises ``LookupError`` and nothing is clicked.
        """
        block, count = self._located()
        positions = _matching(block, choice)
        if len(positions) != 1:
            index = _shown_index(self._index, count)
            raise LookupError(
                _several(self._group.name, choice, index)
                if positions
                else _no_choice(self._group.name, choice, [(index, _choices(block))])
            )
        _click(block, positions[0], self._group._follow)

    def clear(self) -> None:
        """Clear the filter through the choice that removes its parameters, "All" or "Any
        date" as a rule, and wait for the page it leads to.

        Nothing is clicked when the filter isn't applied. A filter applied without a choice
        that clears it, such as one of the project's own without "All", raises ``LookupError``.
        """
        block, _ = self._located()
        hrefs = _hrefs(block)
        own = _own_parameters(hrefs)
        if not own & set(_query(block.page.url)):
            return
        clearing = [position for position, href in enumerate(hrefs) if not own & set(_query(href))]
        if not clearing:
            # The page offers no way to clear this filter alone. Going to a URL without its
            # parameters would do what no link does, and "Clear all filters" would clear the
            # others too, so the test is pointed to that instead.
            raise LookupError(
                f"The filter on {self._group.name!r} offers no choice that clears it. "
                "Clear every filter with page.filters.clear()."
            )
        _click(block, clearing[0], self._group._follow)

    def _located(self) -> tuple[Locator, int]:
        """The filter's ``ul``, and how many filters its field has now."""
        blocks = self._group._read()
        if self._index >= len(blocks):
            raise LookupError(
                f"The page no longer shows a filter on {self._group.name!r} at index "
                f"{self._index}; it shows {len(blocks)}."
            )
        return blocks[self._index], len(blocks)

    def __repr__(self) -> str:
        return f"FieldFilter({self._group.name!r}, {self._index})"


class FieldFilters(Sequence[FieldFilter]):
    """The filters on one field, in the order the page shows them. Most fields have one.

    The filters are found on the page again each time they are used, by the field they
    filter. ``shown`` gives the page once it is known to be the changelist they are on, and
    ``follow`` clicks a link on it and waits for the page it leads to.
    """

    def __init__(
        self,
        name: str,
        shown: Callable[[], Page],
        model: type[Model],
        follow: Callable[[Locator], None],
    ) -> None:
        self._name = name
        self._shown = shown
        self._model = model
        self._follow = follow

    @property
    def name(self) -> str:
        """The field the filters are addressed by, as in ``page.filters[name]``."""
        return self._name

    @property
    def native(self) -> Locator | list[Locator]:
        """The filter's ``ul`` of links, or a list of them for a field with several filters."""
        blocks = self._read()
        return blocks[0] if len(blocks) == 1 else blocks

    @property
    def choices(self) -> list[str] | list[list[str]]:
        """The filter's ``choices``, or a list of them for a field with several filters."""
        choices = [_choices(block) for block in self._read()]
        return choices[0] if len(choices) == 1 else choices

    @property
    def selected(self) -> str | list[str | None] | None:
        """The filter's ``selected``, or a list of them for a field with several filters."""
        selected = [_selected(block) for block in self._read()]
        return selected[0] if len(selected) == 1 else selected

    def apply(self, choice: str) -> None:
        """Apply ``choice`` through whichever of the field's filters offers it, as
        ``FieldFilter.apply`` does.

        A label that more than one of the filters offers, such as "All", raises ``LookupError``
        naming them by index, so it is applied through one of them, as in ``group[1]``.
        """
        blocks = self._read()
        found = [
            (index, block, position)
            for index, block in enumerate(blocks)
            for position in _matching(block, choice)
        ]
        if len(found) == 1:
            _, block, position = found[0]
            _click(block, position, self._follow)
            return
        if not found:
            choices = [
                (_shown_index(index, len(blocks)), _choices(block))
                for index, block in enumerate(blocks)
            ]
            raise LookupError(_no_choice(self._name, choice, choices))
        offering = sorted({index for index, _, _ in found})
        if len(offering) == 1:
            raise LookupError(_several(self._name, choice, _shown_index(offering[0], len(blocks))))
        raise LookupError(
            f"The filters on {self._name!r} at index {_and(offering)} each offer {choice!r}. "
            f"Apply it through one of them, such as "
            f"page.filters[{self._name!r}][{offering[0]}].apply({choice!r})."
        )

    def clear(self) -> None:
        """Clear each of the field's filters that is applied, in the order shown, as
        ``FieldFilter.clear`` does.

        A click that already cleared a later filter saves that filter's click, as "Any date"
        does for an empty filter on the same field.
        """
        for item in self:
            item.clear()

    @overload
    def __getitem__(self, index: int) -> FieldFilter: ...

    @overload
    def __getitem__(self, index: slice) -> list[FieldFilter]: ...

    def __getitem__(self, index: int | slice) -> FieldFilter | list[FieldFilter]:
        count = len(self)
        if isinstance(index, slice):
            return [FieldFilter(self, position) for position in range(count)[index]]
        if not -count <= index < count:
            raise IndexError(
                f"The field {self._name!r} has {count} filter{'' if count == 1 else 's'}, "
                f"so there is none at index {index}."
            )
        # A negative index becomes the position it stands for now, so a held filter keeps
        # meaning that position and fails if the page no longer has it.
        return FieldFilter(self, index % count)

    def __len__(self) -> int:
        return len(self._read())

    def __iter__(self) -> Iterator[FieldFilter]:
        return iter([FieldFilter(self, position) for position in range(len(self))])

    def __repr__(self) -> str:
        return f"FieldFilters({self._name!r})"

    def _read(self) -> list[Locator]:
        blocks = _filter_blocks(self._shown(), self._model).get(self._name)
        if blocks is None:
            raise LookupError(f"The page no longer shows a filter on {self._name!r}.")
        return blocks


class ChangelistFilters(Mapping[str, FieldFilters]):
    """The filters a changelist offers, by the field they filter, in the order the page
    shows them.

    A read-only mapping that reads the page each time it is used, as each group of filters
    does. A miss lists the fields there are. ``shown`` gives the page once it is known to be
    the changelist the filters are on, ``model`` is the changelist's model, and ``follow``
    clicks a link on the page and waits for the page it leads to.
    """

    def __init__(
        self,
        shown: Callable[[], Page],
        model: type[Model],
        follow: Callable[[Locator], None],
    ) -> None:
        self._shown = shown
        self._model = model
        self._follow = follow

    def __getitem__(self, key: str) -> FieldFilters:
        names = self._names()
        if key not in names:
            listed = ", ".join(repr(name) for name in names) or "none"
            raise KeyError(f"No filter on a field named {key!r} here. Fields: {listed}.")
        return FieldFilters(key, self._shown, self._model, self._follow)

    def __iter__(self) -> Iterator[str]:
        return iter(self._names())

    def __len__(self) -> int:
        return len(self._names())

    def clear(self) -> None:
        """Click the admin's "Clear all filters" and wait for the page it leads to.

        The admin keeps a search and the ordering. It shows the link only while a filter is
        applied, so nothing is clicked otherwise. A changelist without filters raises
        ``LookupError``.
        """
        page = self._shown()
        link = page.locator(_CLEAR_ALL)
        if link.count():
            self._follow(link.first)
        elif not _filter_blocks(page, self._model):
            raise LookupError("The page offers no filters.")

    def __repr__(self) -> str:
        return f"ChangelistFilters({self._names()!r})"

    def _names(self) -> list[str]:
        return list(_filter_blocks(self._shown(), self._model))


def _filter_blocks(page: Page, model: type[Model]) -> dict[str, list[Locator]]:
    """The filters ``page`` shows, by the field each filters, in the order shown.

    A filter is a ``ul`` of links in the sidebar. A ``ul`` whose links send no parameter of
    their own, such as one that lays out a custom filter's inputs, is not one.
    """
    lists = page.locator("#changelist-filter ul")
    hrefs = lists.evaluate_all(
        "uls => uls.map(ul => Array.from(ul.querySelectorAll('a[href]'),"
        " a => a.getAttribute('href')))"
    )
    blocks: dict[str, list[Locator]] = {}
    for index, links in enumerate(hrefs):
        parameters = _own_parameters(links)
        if parameters:
            blocks.setdefault(_field_of(model, parameters), []).append(lists.nth(index))
    return blocks


def _field_of(model: type[Model], parameters: Iterable[str]) -> str:
    """The field a filter of ``model``'s changelist filters, from the parameters its links
    send.

    Each parameter loses a trailing lookup and then a relation's target field. When the
    results differ, the part they share up to a ``__`` is used, or else the first of them.
    """
    names = sorted({_reduced(model, parameter) for parameter in parameters})
    if len(names) == 1:
        return names[0]
    shared: list[str] = []
    for parts in zip(*(name.split("__") for name in names)):
        if len(set(parts)) > 1:
            break
        shared.append(parts[0])
    return "__".join(shared) if shared else names[0]


def _choices(block: Locator) -> list[str]:
    return [" ".join(text.split()) for text in block.locator("a").all_text_contents()]


def _selected(block: Locator) -> str | None:
    labels = block.locator("li.selected a").all_text_contents()
    return " ".join(labels[0].split()) if labels else None


def _matching(block: Locator, choice: str) -> list[int]:
    """The positions of the links labeled ``choice``, with or without the count Django adds."""
    if not isinstance(choice, str):
        return []
    counted = re.compile(re.escape(choice) + r" \((?:\d+|-)\)")
    return [
        position
        for position, label in enumerate(_choices(block))
        if label == choice or counted.fullmatch(label)
    ]


def _click(block: Locator, position: int, follow: Callable[[Locator], None]) -> None:
    # A filter the user collapsed hides its links, and a hidden link can't be clicked.
    block.evaluate("ul => { const box = ul.closest('details'); if (box) box.open = true; }")
    follow(block.locator("a").nth(position))


def _no_choice(name: str, choice: str, choices: list[tuple[int | None, list[str]]]) -> str:
    lines = [f"No filter on {name!r} offers {choice!r}.", "", "Choices:"]
    lines += [
        "    " + ("" if index is None else f"[{index}] ") + ", ".join(map(repr, labels))
        for index, labels in choices
    ]
    return "\n".join(lines)


def _several(name: str, choice: str, index: int | None) -> str:
    where = "" if index is None else f" at index {index}"
    return f"The filter on {name!r}{where} offers {choice!r} more than once."


def _shown_index(index: int, count: int) -> int | None:
    # A message names a filter by its index only when its field has several.
    return index if count > 1 else None


def _and(items: list[int]) -> str:
    words = [str(item) for item in items]
    return " and ".join([", ".join(words[:-1]), words[-1]]) if len(words) > 1 else words[0]


def _hrefs(block: Locator) -> list[str]:
    # Every link, in the order of `_choices`, so a position names the same link in both.
    hrefs: list[str] = block.evaluate(
        "ul => Array.from(ul.querySelectorAll('a'), a => a.getAttribute('href') || '')"
    )
    return hrefs


def _query(url: str) -> dict[str, list[str]]:
    return parse_qs(urlsplit(url).query, keep_blank_values=True)


def _own_parameters(hrefs: list[str]) -> set[str]:
    # Each link is the whole URL the page would have after the click, so it repeats what
    # is already applied, such as a search or another filter's value, unchanged in every
    # link. The filter's own parameters are the ones its links don't all send alike: its
    # first link ("All") usually removes them, and its other links set them to different
    # values, which is also how a filter of the project's own without "All" is told.
    sent = [_query(href) for href in hrefs]
    names: set[str] = set().union(*sent)
    return {name for name in names if len({_sent_as(values, name) for values in sent}) > 1}


def _sent_as(values: dict[str, list[str]], name: str) -> tuple[str, ...] | None:
    # A link that leaves the parameter out differs from one that sends it empty.
    return tuple(values[name]) if name in values else None


def _reduced(model: type[Model], parameter: str) -> str:
    parts = parameter.split("__")
    # `isempty` is the admin's own and no lookup the ORM knows.
    if len(parts) > 1 and (parts[-1] == "isempty" or _has_lookup(model, parts[:-1], parts[-1])):
        parts = parts[:-1]
    if len(parts) > 1 and _is_relation_target(model, parts):
        parts = parts[:-1]
    return "__".join(parts)


def _fields(model: type[Model], parts: list[str]) -> list[Field] | None:
    try:
        fields: list[Field] = get_fields_from_path(model, "__".join(parts))
    except (FieldDoesNotExist, NotRelationField):
        return None
    return fields


def _has_lookup(model: type[Model], parts: list[str], lookup: str) -> bool:
    fields = _fields(model, parts)
    return fields is not None and fields[-1].get_lookup(lookup) is not None


def _is_relation_target(model: type[Model], parts: list[str]) -> bool:
    # A related filter matches on the relation's target, `category__id` once the lookup is
    # removed, which is the relation itself to the user.
    fields = _fields(model, parts)
    if fields is None or len(fields) < 2 or not fields[-2].is_relation:
        return False
    target = getattr(fields[-2], "target_field", None)
    return target is not None and target.name == parts[-1]
