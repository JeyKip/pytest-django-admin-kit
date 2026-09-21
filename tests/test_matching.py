"""How a row pattern is matched and how a miss is reported, without a browser.

The rows are stand-ins with the things matching reads: a row is a sequence of cells, and
a cell has a value and links.
"""

from urllib.parse import urlsplit

import pytest

from django_admin_kit.matching import ANY, ANY_ROW, contains, match, matches
from django_admin_kit.rendered import Link


class FakeCell:
    def __init__(self, value, links=()):
        self.value = value
        self.links = list(links)


class FakeRow:
    """Built from values, or from cells where a cell needs links; named columns where a
    pattern addresses them by name."""

    def __init__(self, *cells, columns=()):
        self._cells = [cell if isinstance(cell, FakeCell) else FakeCell(cell) for cell in cells]
        self._columns = list(columns)

    def __len__(self):
        return len(self._cells)

    def __iter__(self):
        return iter(self._cells)

    def __getitem__(self, key):
        if isinstance(key, str):
            if key not in self._columns:
                raise KeyError(f"The row has no column named {key!r}.")
            key = self._columns.index(key)
        return self._cells[key]


ROWS = [
    FakeRow(1, "Janet", "Doe", "Active"),
    FakeRow(2, "John", "Doe", ""),
    FakeRow(3, "Jane", "Roe", True),
]

COLUMNS = ("id", "first_name", "last_name", "status")
NAMED = [
    FakeRow(*values, columns=COLUMNS)
    for values in ((1, "Janet", "Doe", "Active"), (2, "John", "Doe", ""))
]

EDIT = "/admin/shop/product/1/change/"
DOCUMENTS = [Link("Datasheet", "/media/a.pdf"), Link("Manual", "/media/b.pdf")]
LINKED = FakeRow(
    FakeCell("Bolt", [Link("Bolt", EDIT)]), "SKU-Bolt", FakeCell("Datasheet Manual", DOCUMENTS)
)


def test_a_row_matches_literal_values_cell_by_cell():
    assert matches((1, "Janet", "Doe", "Active"), ROWS[0])
    assert matches([1, "Janet", "Doe", "Active"], ROWS[0])


def test_one_different_value_is_no_match():
    assert not matches((1, "Jane", "Doe", "Active"), ROWS[0])


def test_a_pattern_of_another_length_is_no_match():
    assert not matches((1, "Janet", "Doe"), ROWS[0])
    assert not matches((1, "Janet", "Doe", "Active", "extra"), ROWS[0])


def test_an_empty_string_matches_an_empty_cell_and_nothing_else():
    assert matches((2, "John", "Doe", ""), ROWS[1])
    assert not matches((1, "Janet", "Doe", ""), ROWS[0])


def test_a_boolean_matches_a_boolean_and_not_its_name():
    assert matches((3, "Jane", "Roe", True), ROWS[2])
    assert not matches((3, "Jane", "Roe", "True"), ROWS[2])


def test_contains_passes_when_any_row_matches():
    assert contains((2, "John", "Doe", ""), ROWS) is True


def test_contains_shows_the_pattern_and_every_row_when_none_matches():
    with pytest.raises(AssertionError) as error:
        contains((1, "Jane", "Doe", "Active"), ROWS)

    assert str(error.value) == "\n".join(
        [
            "Expected row:",
            "    (1, 'Jane', 'Doe', 'Active')",
            "",
            "No matching row found.",
            "",
            "Actual rows:",
            "    (1, 'Janet', 'Doe', 'Active')",
            "    (2, 'John', 'Doe', '')",
            "    (3, 'Jane', 'Roe', True)",
        ]
    )


def test_contains_says_so_when_there_are_no_rows_at_all():
    with pytest.raises(AssertionError, match=r"Actual rows:\n    \(none\)$"):
        contains((1, "Jane", "Doe", "Active"), [])


def test_a_link_matches_a_cell_that_renders_that_one_link():
    assert matches((Link("Bolt", EDIT), "SKU-Bolt", "Datasheet Manual"), LINKED)
    assert matches((Link("Bolt", urlsplit(EDIT)), "SKU-Bolt", "Datasheet Manual"), LINKED)


def test_a_pair_is_a_link_too():
    assert matches((("Bolt", EDIT), "SKU-Bolt", "Datasheet Manual"), LINKED)
    assert matches((["Bolt", urlsplit(EDIT)], "SKU-Bolt", "Datasheet Manual"), LINKED)
    assert not matches((("Nut", EDIT), "SKU-Bolt", "Datasheet Manual"), LINKED)


def test_a_link_with_another_href_or_text_is_no_match():
    other = Link("Bolt", "/admin/shop/product/2/change/")
    assert not matches((other, "SKU-Bolt", "Datasheet Manual"), LINKED)
    assert not matches((Link("Nut", EDIT), "SKU-Bolt", "Datasheet Manual"), LINKED)


def test_a_link_does_not_match_a_cell_without_a_link():
    assert not matches(("Bolt", Link("SKU-Bolt", "/anywhere/"), "Datasheet Manual"), LINKED)


def test_a_list_of_links_matches_the_links_exactly_and_in_order():
    links = [Link("Datasheet", "/media/a.pdf"), Link("Manual", "/media/b.pdf")]

    assert matches(("Bolt", "SKU-Bolt", links), LINKED)
    assert matches(("Bolt", "SKU-Bolt", tuple(links)), LINKED)
    assert matches(("Bolt", "SKU-Bolt", [("Datasheet", "/media/a.pdf"), links[1]]), LINKED)
    assert not matches(("Bolt", "SKU-Bolt", list(reversed(links))), LINKED)
    assert not matches(("Bolt", "SKU-Bolt", links[:1]), LINKED)


def test_an_empty_list_matches_a_cell_without_links():
    assert matches(("Bolt", [], "Datasheet Manual"), LINKED)
    assert matches(("Bolt", (), "Datasheet Manual"), LINKED)
    assert not matches(([], "SKU-Bolt", "Datasheet Manual"), LINKED)


def test_a_pattern_matches_the_value_or_the_links_whatever_its_shape():
    """A project's own rule may put a pair or the links themselves into the value."""
    pair = ("Bolt", "SKU-Bolt")
    row = FakeRow(FakeCell(pair), FakeCell(DOCUMENTS), FakeCell(pair, [Link("x", "/y")]))

    assert matches((pair, DOCUMENTS, pair), row)
    assert not matches((("Bolt", "SKU-Nut"), DOCUMENTS, pair), row)


def test_a_miss_on_a_link_shows_the_links_the_cell_has():
    with pytest.raises(AssertionError) as error:
        contains((("Nut", EDIT), "SKU-Bolt", [Link("Manual", "/media/b.pdf")]), [LINKED])

    assert str(error.value).endswith(
        "Actual rows:\n"
        "    ([Link('Bolt', '/admin/shop/product/1/change/')], 'SKU-Bolt', "
        "[Link('Datasheet', '/media/a.pdf'), Link('Manual', '/media/b.pdf')])"
    )


def test_any_stands_for_one_cell_whatever_it_holds():
    assert matches((1, ANY, "Doe", ANY), ROWS[0])
    assert matches((ANY, ANY, ANY, ANY), ROWS[1])
    assert not matches((1, ANY, "Doe"), ROWS[0])


def test_any_row_matches_every_row():
    assert all(matches(ANY_ROW, row) for row in ROWS)
    assert contains(ANY_ROW, ROWS) is True


def test_any_row_still_needs_a_row():
    with pytest.raises(AssertionError, match=r"Expected row:\n    ANY_ROW\n"):
        contains(ANY_ROW, [])


def test_the_sentinels_print_as_their_names():
    with pytest.raises(AssertionError, match=r"Expected row:\n    \(1, 'Jane', 'Doe', ANY\)\n"):
        contains((1, "Jane", "Doe", ANY), ROWS)


def test_a_callable_decides_by_its_truth():
    assert matches((1, lambda row, cell: cell.value.startswith("Jan"), "Doe", "Active"), ROWS[0])
    assert not matches((1, lambda row, cell: cell.value.startswith("Jo"), "Doe", "Active"), ROWS[0])
    assert matches((1, "Janet", "Doe", lambda row, cell: len(cell.value)), ROWS[0])
    assert not matches((2, "John", "Doe", lambda row, cell: len(cell.value)), ROWS[1])


def test_a_callable_sees_the_whole_row_and_the_cell():
    def first_name_matches_link(row, cell):
        return cell.links[0].text == row[0].value

    assert matches((first_name_matches_link, "SKU-Bolt", ANY), LINKED)


def test_a_callable_that_raises_is_left_to_raise():
    def broken(row, cell):
        raise KeyError("the test's own bug")

    with pytest.raises(KeyError, match="own bug"):
        matches((1, broken, "Doe", "Active"), ROWS[0])


def test_a_callable_is_named_in_the_failure():
    def valid_email(row, cell):
        return False

    with pytest.raises(
        AssertionError, match=r"Expected row:\n    \(1, 'Jane', valid_email, <lambda>\)\n"
    ):
        contains((1, "Jane", valid_email, lambda row, cell: True), ROWS)


def test_a_dictionary_matches_the_columns_it_names_and_leaves_the_rest_open():
    assert matches({"first_name": "Janet"}, NAMED[0])
    assert matches(
        {"last_name": "Doe", "status": ANY, "id": lambda row, cell: cell.value < 2}, NAMED[0]
    )
    assert not matches({"first_name": "Janet", "status": ""}, NAMED[0])


def test_an_empty_dictionary_matches_any_row():
    assert matches({}, NAMED[0])


def test_a_dictionary_naming_an_unknown_column_is_a_mistake_not_a_miss():
    with pytest.raises(KeyError, match="no column named 'email'"):
        matches({"email": "jane@example.com"}, NAMED[0])


def test_a_miss_by_columns_shows_only_the_columns_named():
    def short(row, cell):
        return len(cell.value) < 3

    with pytest.raises(AssertionError) as error:
        contains({"first_name": short, "status": "Active"}, NAMED)

    assert str(error.value) == "\n".join(
        [
            "Expected row:",
            "    {'first_name': short, 'status': 'Active'}",
            "",
            "No matching row found.",
            "",
            "Actual rows:",
            "    {'first_name': 'Janet', 'status': 'Active'}",
            "    {'first_name': 'John', 'status': ''}",
        ]
    )


def test_match_passes_when_every_row_is_where_its_pattern_says():
    patterns = [(1, "Janet", "Doe", "Active"), (2, "John", ANY, ""), (3, "Jane", "Roe", True)]

    assert match(patterns, ROWS) is True
    assert match(tuple(patterns), ROWS) is True


def test_match_lets_any_row_hold_a_position():
    assert match([ANY_ROW, (2, "John", "Doe", ""), ANY_ROW], ROWS) is True


def test_match_on_no_rows_takes_no_patterns():
    assert match([], []) is True


def test_match_fails_on_the_right_rows_in_the_wrong_order():
    with pytest.raises(AssertionError, match=r"Row 0 did not match:\n"):
        match([(2, "John", "Doe", ""), (1, "Janet", "Doe", "Active"), ANY_ROW], ROWS)


def test_match_reports_every_row_that_did_not_match():
    with pytest.raises(AssertionError) as error:
        match([{"first_name": "Jane"}, {"first_name": "Joan"}], NAMED)

    assert str(error.value) == "\n".join(
        [
            "Expected rows:",
            "    {'first_name': 'Jane'}",
            "    {'first_name': 'Joan'}",
            "",
            "Row 0 did not match:",
            "    expected {'first_name': 'Jane'}",
            "    actual   {'first_name': 'Janet'}",
            "",
            "Row 1 did not match:",
            "    expected {'first_name': 'Joan'}",
            "    actual   {'first_name': 'John'}",
            "",
            "Actual rows:",
            "    (1, 'Janet', 'Doe', 'Active')",
            "    (2, 'John', 'Doe', '')",
        ]
    )


def test_match_fails_on_a_different_number_of_rows():
    with pytest.raises(AssertionError, match=r"Expected 2 rows, found 3\.\n"):
        match([ANY_ROW, ANY_ROW], ROWS)
    with pytest.raises(AssertionError, match=r"Expected 1 row, found 0\.\n"):
        match([ANY_ROW], [])


def test_match_takes_a_list_of_rows_not_one_row():
    with pytest.raises(TypeError, match=r"written as \[row\]"):
        match(ANY_ROW, ROWS)
    with pytest.raises(TypeError, match=r"written as \[row\]"):
        match({"first_name": "Janet"}, NAMED)


def test_a_wrong_count_shows_the_patterns_and_the_rows():
    with pytest.raises(AssertionError) as error:
        match([{"first_name": "Janet"}], NAMED)

    assert str(error.value) == "\n".join(
        [
            "Expected rows:",
            "    {'first_name': 'Janet'}",
            "",
            "Expected 1 row, found 2.",
            "",
            "Actual rows:",
            "    (1, 'Janet', 'Doe', 'Active')",
            "    (2, 'John', 'Doe', '')",
        ]
    )


def test_a_wrong_row_shows_its_position_and_both_sides():
    with pytest.raises(AssertionError) as error:
        match([ANY_ROW, {"first_name": "Jane", "status": ANY}], NAMED)

    assert str(error.value) == "\n".join(
        [
            "Expected rows:",
            "    ANY_ROW",
            "    {'first_name': 'Jane', 'status': ANY}",
            "",
            "Row 1 did not match:",
            "    expected {'first_name': 'Jane', 'status': ANY}",
            "    actual   {'first_name': 'John', 'status': ''}",
            "",
            "Actual rows:",
            "    (1, 'Janet', 'Doe', 'Active')",
            "    (2, 'John', 'Doe', '')",
        ]
    )


@pytest.mark.parametrize("pattern", [(1, "Jane", "Doe", "Active"), [1, "Jane", "Doe", "Active"]])
def test_a_wrong_row_is_shown_as_written_next_to_the_rows_values(pattern):
    with pytest.raises(AssertionError) as error:
        match([pattern, ANY_ROW], NAMED)

    assert str(error.value) == "\n".join(
        [
            "Expected rows:",
            f"    {pattern!r}",
            "    ANY_ROW",
            "",
            "Row 0 did not match:",
            f"    expected {pattern!r}",
            "    actual   (1, 'Janet', 'Doe', 'Active')",
            "",
            "Actual rows:",
            "    (1, 'Janet', 'Doe', 'Active')",
            "    (2, 'John', 'Doe', '')",
        ]
    )


def test_a_wrong_row_asking_for_one_link_shows_the_links_the_cell_has():
    pattern = (("Nut", EDIT), "SKU-Bolt", "Datasheet Manual")

    with pytest.raises(AssertionError) as error:
        match([pattern], [LINKED])

    assert str(error.value) == "\n".join(
        [
            "Expected rows:",
            f"    {pattern!r}",
            "",
            "Row 0 did not match:",
            f"    expected {pattern!r}",
            f"    actual   ([Link('Bolt', {EDIT!r})], 'SKU-Bolt', 'Datasheet Manual')",
            "",
            "Actual rows:",
            "    ('Bolt', 'SKU-Bolt', 'Datasheet Manual')",
        ]
    )


def test_a_wrong_row_asking_for_two_links_shows_the_links_the_cell_has():
    pattern = ("Bolt", "SKU-Bolt", [("Manual", "/media/b.pdf"), ("Datasheet", "/media/a.pdf")])

    with pytest.raises(AssertionError) as error:
        match([pattern], [LINKED])

    assert str(error.value) == "\n".join(
        [
            "Expected rows:",
            f"    {pattern!r}",
            "",
            "Row 0 did not match:",
            f"    expected {pattern!r}",
            "    actual   ('Bolt', 'SKU-Bolt', "
            "[Link('Datasheet', '/media/a.pdf'), Link('Manual', '/media/b.pdf')])",
            "",
            "Actual rows:",
            "    ('Bolt', 'SKU-Bolt', 'Datasheet Manual')",
        ]
    )
