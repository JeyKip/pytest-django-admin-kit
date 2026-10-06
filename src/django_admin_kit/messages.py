"""The messages the admin shows after an operation, with their level.

A level is the tag a message is drawn with, not a fixed name: Django's own tags merged
with the project's ``MESSAGE_TAGS``, so a project that tags errors ``danger`` reads them
as ``danger``.
"""

from __future__ import annotations

from typing import Callable, Iterator, Sequence, overload

from django.contrib.messages.utils import get_level_tags
from playwright.sync_api import Locator

from .rendered import text_of


class Message:
    """One message: its ``level``, the tag it is drawn with, and its ``text``.

    A message compares equal to another message and to a ``(level, text)`` pair, as a
    tuple or a list, and to nothing else.
    """

    def __init__(self, level: str, text: str) -> None:
        self._level = level
        self._text = text

    @property
    def level(self) -> str:
        """The level's tag, or ``""`` when the message's level has none."""
        return self._level

    @property
    def text(self) -> str:
        return self._text

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Message):
            return (self._level, self._text) == (other._level, other._text)
        if isinstance(other, (tuple, list)) and len(other) == 2:
            return (self._level, self._text) == tuple(other)
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self._level, self._text))

    def __repr__(self) -> str:
        return f"Message({self._level!r}, {self._text!r})"


class Messages(Sequence[Message]):
    """The messages a page shows, in order, read from the page each time they are used.

    ``items`` gives the elements of the messages, and fails when the browser no longer
    shows the page they are on.
    """

    def __init__(self, items: Callable[[], Locator]) -> None:
        self._items = items

    @overload
    def __getitem__(self, index: int) -> Message: ...

    @overload
    def __getitem__(self, index: slice) -> list[Message]: ...

    def __getitem__(self, index: int | slice) -> Message | list[Message]:
        return self._read()[index]

    def __len__(self) -> int:
        return len(self._read())

    # The page is read once for the whole loop or lookup, rather than once per message as
    # the sequence's own versions would.
    def __iter__(self) -> Iterator[Message]:
        return iter(self._read())

    def __contains__(self, message: object) -> bool:
        return message in self._read()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, (Messages, list, tuple)):
            return self._read() == list(other)
        return NotImplemented

    __hash__ = None  # type: ignore[assignment]

    def of_level(self, level: str) -> list[str]:
        """The texts of the messages of ``level``, in order; ``[]`` when there are none.

        ``level`` is a tag the project knows, or ``""`` for messages whose level has no
        tag. Any other name raises ``KeyError`` listing the levels there are, because a
        level the project renamed would otherwise read as no messages and let a test pass.
        """
        # Django lists its own levels first, in their order, then the ones the project adds.
        levels = list(dict.fromkeys(get_level_tags().values()))
        if level and level not in levels:
            raise KeyError(
                f"The project has no message level {level!r}. Levels: "
                f"{', '.join(repr(name) for name in levels)}."
            )
        return [message.text for message in self._read() if message.level == level]

    def __repr__(self) -> str:
        return f"Messages({self._read()!r})"

    def _read(self) -> list[Message]:
        # Every message is read with the same levels, so they are looked up once.
        levels = set(get_level_tags().values())
        return [Message(_level(item, levels), text_of(item)) for item in self._items().all()]


def _level(item: Locator, levels: set[str]) -> str:
    """The level tag among the classes of ``item``, or ``""`` when it has none.

    Django draws a message with its extra tags and then its level tag, so the last class
    that is a level tag is the level, even when an extra tag spells one too.
    """
    classes = (item.get_attribute("class") or "").split()
    return next((tag for tag in reversed(classes) if tag in levels), "")
