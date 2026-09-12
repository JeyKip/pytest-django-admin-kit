"""The count reader, fed the paginator's own text as each Django version and
localization renders it, without a browser.

The browser tests in `test_changelist.py` prove the text is read from the right
element; these prove what is made of it.
"""

import pytest
from django.contrib import admin

from django_admin_kit.pages import ChangelistPage
from django_admin_kit.urls import AdminUrls


class FakePaginator:
    def __init__(self, text):
        self.text = text

    def evaluate(self, expression):
        return self.text


class FakePage:
    """A changelist that opened, whose paginator says `text`."""

    url = "http://localhost:8000/admin/shop/product/"

    def __init__(self, text):
        self.text = text

    def locator(self, selector):
        assert selector == "#changelist .paginator"
        return FakePaginator(self.text)


def changelist(text):
    return ChangelistPage(FakePage(text), 200, "/admin/shop/product/", AdminUrls(admin.site))


@pytest.mark.parametrize(
    ("text", "count", "summary"),
    [
        # Django up to 5.2: the count sits between the paginator's line breaks.
        ("\n\n3 products\n\n\n", 3, "3 products"),
        # Django 6.0 onwards: indented, after the heading and the page links.
        ("\n    \n0 products\n\n", 0, "0 products"),
        # Before 6.0 the ellipsis between page links is loose text too.
        ("\n\n… \n\n101 products\n\n", 101, "101 products"),
        ("1 product", 1, "1 product"),
        # A project that localizes numbers groups them, with its locale's separator.
        ("1,000 products", 1000, "1,000 products"),
        ("1.000 products", 1000, "1.000 products"),
        ("1\xa0000 products", 1000, "1 000 products"),
        ("1 000 products", 1000, "1 000 products"),
    ],
)
def test_the_count_and_its_wording_are_read_from_the_paginator(text, count, summary):
    page = changelist(text)

    assert page.count == count
    assert page.summary == summary
    assert page.empty is (count == 0)


def test_a_paginator_that_reports_no_count_is_a_loud_failure():
    """A template override that drops the count is a bug to see, not a zero."""
    page = changelist("Nothing to see")

    with pytest.raises(AssertionError, match="unexpected paginator text"):
        _ = page.count
