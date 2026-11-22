"""How a file read from a file field compares, without a browser.

A test writes the pair it expects; the file decides whether it is that pair, and never
guesses which of its two parts a bare string means.
"""

from urllib.parse import urlsplit

from django_admin_kit.fields import FormFile

NAME = "manuals/assembly.txt"
HREF = "/media/manuals/assembly.txt"
SPLIT = urlsplit(HREF)


def test_a_file_equals_a_file_with_the_same_name_and_href():
    assert FormFile(NAME, HREF) == FormFile(NAME, HREF)
    assert FormFile(NAME, HREF) == FormFile(NAME, SPLIT)
    assert FormFile("wiring.txt", None) == FormFile("wiring.txt", None)


def test_a_file_with_another_part_is_a_different_file():
    assert FormFile(NAME, HREF) != FormFile("manuals/wiring.txt", HREF)
    assert FormFile(NAME, HREF) != FormFile(NAME, "/media/manuals/wiring.txt")
    assert FormFile(NAME, HREF) != FormFile(NAME, None)


def test_a_file_equals_the_pair_it_is_made_of():
    assert FormFile(NAME, HREF) == (NAME, HREF)
    assert FormFile(NAME, HREF) == (NAME, SPLIT)
    assert FormFile(NAME, HREF) == [NAME, HREF]
    assert FormFile("wiring.txt", None) == ("wiring.txt", None)


def test_a_pair_on_the_left_defers_to_the_file():
    """What a list comparison does for each element: the tuple returns NotImplemented and
    Python asks the file."""
    for expected in ((NAME, HREF), [NAME, HREF]):
        assert expected == FormFile(NAME, HREF)


def test_a_file_is_not_its_name_as_a_string():
    assert FormFile(NAME, HREF) != NAME
    assert FormFile("wiring.txt", None) != "wiring.txt"


def test_a_file_is_not_a_pair_of_something_else():
    assert FormFile(NAME, HREF) != (NAME, 1)
    assert FormFile(NAME, HREF) != (NAME, HREF, "extra")


def test_the_href_is_split_into_its_parts():
    assert FormFile(NAME, HREF).href.path == HREF
    assert FormFile("wiring.txt", None).href is None


def test_a_file_hashes_like_its_parts():
    assert hash(FormFile(NAME, HREF)) == hash((NAME, SPLIT))
    assert {FormFile(NAME, HREF), FormFile(NAME, SPLIT)} == {FormFile(NAME, HREF)}


def test_a_file_shows_its_href_as_rendered():
    assert repr(FormFile(NAME, HREF)) == f"FormFile({NAME!r}, {HREF!r})"
    assert repr(FormFile("wiring.txt", None)) == "FormFile('wiring.txt', None)"
