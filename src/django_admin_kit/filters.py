"""The filters a changelist offers in its sidebar, grouped by the field they filter.

The page never says which ``list_filter`` entry a filter came from, and its title is the
field's verbose name, which repeats and is translated. What a filter does say is which URL
parameters its links send, so a filter is named after those, reduced to the field.
"""

from __future__ import annotations

from typing import Callable, Iterable, Iterator, Mapping, Sequence, overload
from urllib.parse import parse_qs, urlsplit

from django.contrib.admin.utils import NotRelationField, get_fields_from_path
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Field, Model
from playwright.sync_api import Locator, Page


class FieldFilter:
    """One filter in the sidebar: the one at its position among its field's filters, read
    each time it is used."""

    def __init__(self, group: FieldFilters, index: int) -> None:
        self._group = group
        self._index = index

    @property
    def native(self) -> Locator:
        """The filter's ``ul`` of links, unwrapped, for anything the package does not model."""
        blocks = self._group._read()
        if self._index >= len(blocks):
            raise LookupError(
                f"The page no longer shows a filter on {self._group.name!r} at index "
                f"{self._index}; it shows {len(blocks)}."
            )
        return blocks[self._index]

    def __repr__(self) -> str:
        return f"FieldFilter({self._group.name!r}, {self._index})"


class FieldFilters(Sequence[FieldFilter]):
    """The filters on one field, in the order the page shows them. Most fields have one.

    The filters are found on the page again each time they are used, by the field they
    filter. ``shown`` gives the page once it is known to be the changelist they are on.
    """

    def __init__(self, name: str, shown: Callable[[], Page], model: type[Model]) -> None:
        self._name = name
        self._shown = shown
        self._model = model

    @property
    def name(self) -> str:
        """The field the filters are addressed by, as in ``page.filters[name]``."""
        return self._name

    @property
    def native(self) -> Locator | list[Locator]:
        """The filter's ``ul`` of links, or a list of them for a field with several filters."""
        blocks = self._read()
        return blocks[0] if len(blocks) == 1 else blocks

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
    the changelist the filters are on, and ``model`` is the changelist's model.
    """

    def __init__(self, shown: Callable[[], Page], model: type[Model]) -> None:
        self._shown = shown
        self._model = model

    def __getitem__(self, key: str) -> FieldFilters:
        names = self._names()
        if key not in names:
            listed = ", ".join(repr(name) for name in names) or "none"
            raise KeyError(f"No filter on a field named {key!r} here. Fields: {listed}.")
        return FieldFilters(key, self._shown, self._model)

    def __iter__(self) -> Iterator[str]:
        return iter(self._names())

    def __len__(self) -> int:
        return len(self._names())

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


def _own_parameters(hrefs: list[str]) -> set[str]:
    # Each link is the whole URL the page would have after the click, so it repeats what
    # is already applied, such as a search or another filter's value, unchanged in every
    # link. The filter's own parameters are the ones its links don't all send alike: its
    # first link ("All") usually removes them, and its other links set them to different
    # values, which is also how a filter of the project's own without "All" is told.
    sent = [parse_qs(urlsplit(href).query, keep_blank_values=True) for href in hrefs]
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
