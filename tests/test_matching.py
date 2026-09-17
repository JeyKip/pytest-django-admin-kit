"""How a row pattern is matched and how a miss is reported, without a browser.

The rows are stand-ins with the two things matching reads: a row is a sequence of cells
and a cell has a value.
"""

import pytest

from django_admin_kit.matching import contains, matches


class FakeCell:
    def __init__(self, value):
        self.value = value


class FakeRow:
    def __init__(self, *values):
        self._cells = [FakeCell(value) for value in values]

    def __len__(self):
        return len(self._cells)

    def __iter__(self):
        return iter(self._cells)


ROWS = [
    FakeRow(1, "Janet", "Doe", "Active"),
    FakeRow(2, "John", "Doe", ""),
    FakeRow(3, "Jane", "Roe", True),
]


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
    assert contains(ROWS, (2, "John", "Doe", "")) is True


def test_contains_shows_the_pattern_and_every_row_when_none_matches():
    with pytest.raises(AssertionError) as error:
        contains(ROWS, (1, "Jane", "Doe", "Active"))

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
        contains([], (1, "Jane", "Doe", "Active"))
