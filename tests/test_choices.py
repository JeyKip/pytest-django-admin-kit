"""How a choice read from a select compares, without a browser.

A test writes the pair it expects; the choice decides whether it is that pair, and
never guesses which of its two parts a bare string means.
"""

from django_admin_kit.fields import FieldChoice


def test_a_choice_equals_a_choice_with_the_same_parts():
    assert FieldChoice("3", "Tools") == FieldChoice("3", "Tools")


def test_a_choice_with_another_part_is_a_different_choice():
    assert FieldChoice("3", "Tools") != FieldChoice("3", "Toys")
    assert FieldChoice("3", "Tools") != FieldChoice("4", "Tools")


def test_a_choice_equals_the_pair_it_is_made_of():
    assert FieldChoice("3", "Tools") == ("3", "Tools")
    assert FieldChoice("3", "Tools") == ["3", "Tools"]


def test_a_pair_on_the_left_defers_to_the_choice():
    """What a list comparison does for each element: the tuple returns NotImplemented
    and Python asks the choice."""
    for expected in (("3", "Tools"), ["3", "Tools"]):
        assert expected == FieldChoice("3", "Tools")


def test_a_pair_with_another_part_is_a_different_choice():
    assert FieldChoice("3", "Tools") != ("3", "Toys")
    assert FieldChoice("3", "Tools") != ("4", "Tools")


def test_a_choice_is_not_its_value_as_a_string():
    assert FieldChoice("3", "Tools") != "3"


def test_a_choice_is_not_its_label_as_a_string():
    assert FieldChoice("3", "Tools") != "Tools"


def test_a_choice_is_not_a_pair_of_something_else():
    assert FieldChoice("3", "Tools") != (3, "Tools")
    assert FieldChoice("3", "Tools") != ("3", "Tools", "extra")


def test_a_list_of_choices_compares_to_a_list_of_pairs():
    choices = [FieldChoice("", "---------"), FieldChoice("3", "Tools")]
    assert choices == [("", "---------"), ("3", "Tools")]


def test_a_choice_is_found_among_pairs_and_a_pair_among_choices():
    assert FieldChoice("3", "Tools") in [("", "---------"), ("3", "Tools")]
    assert ("3", "Tools") in [FieldChoice("", "---------"), FieldChoice("3", "Tools")]


def test_a_choice_hashes_like_its_parts():
    assert hash(FieldChoice("3", "Tools")) == hash(("3", "Tools"))
    assert FieldChoice("3", "Tools") in {("3", "Tools")}


def test_a_choice_shows_both_parts():
    assert repr(FieldChoice("3", "Tools")) == "FieldChoice('3', 'Tools')"
