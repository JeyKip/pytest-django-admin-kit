"""Helpers several test modules share. Fixtures go in `conftest.py`; these are plain functions."""


def collect_page_loads(page):
    """The address of each page the browser loads from now on, as a list that grows with them.

    It lets a test check where a step took the browser, page by page.
    """
    loads = []
    page.native.on("load", lambda loaded: loads.append(loaded.url))
    return loads


def count_page_loads(page, change):
    """Run ``change`` and return how many pages the browser loaded meanwhile.

    It tells a step that loads a page once from one that loads twice, or from one that only
    changes the page in place, such as selecting a row or going to the page already shown.
    """
    loads = collect_page_loads(page)
    change()
    return len(loads)
