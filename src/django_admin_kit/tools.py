"""What a session hands to every page it opens."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .normalize import Normalizers
    from .urls import AdminUrls


@dataclass(frozen=True)
class PageTools:
    """What every page of a session reads by: where the admin's pages are, and the rules
    that read the values they render.

    Only what is built once from the settings or the session's fixtures, and is the same
    for every page, belongs here. What belongs to one page, row, cell or field is passed
    to it on its own. A page hands the objects it builds only the tools they use.
    """

    urls: AdminUrls
    normalizers: Normalizers
