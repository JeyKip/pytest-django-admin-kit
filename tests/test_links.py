"""How a link read from a cell compares, without a browser.

A test writes the pair it expects to see; the link decides whether it is that pair.
"""

from urllib.parse import urlsplit

from django_admin_kit.rendered import Link

HREF = "/admin/shop/product/1/change/?_changelist_filters=is_active__exact%3D1"
SPLIT = urlsplit(HREF)


def test_a_link_equals_a_link_with_the_same_text_and_href():
    assert Link("Bolt", HREF) == Link("Bolt", HREF)
    assert Link("Bolt", HREF) == Link("Bolt", SPLIT)
    assert Link("Bolt", SPLIT) == Link("Bolt", HREF)


def test_a_link_equals_the_pair_it_was_rendered_from():
    assert Link("Bolt", HREF) == ("Bolt", HREF)
    assert Link("Bolt", HREF) == ("Bolt", SPLIT)
    assert Link("Bolt", HREF) == ["Bolt", HREF]
    assert Link("Bolt", HREF) == ["Bolt", SPLIT]


def test_a_pair_on_the_left_defers_to_the_link():
    """What a list comparison does for each element: the tuple returns NotImplemented
    and Python asks the link."""
    for expected in (("Bolt", HREF), ("Bolt", SPLIT), ["Bolt", HREF], ["Bolt", SPLIT]):
        assert expected == Link("Bolt", HREF)


def test_a_different_href_is_a_different_link():
    assert Link("Bolt", HREF) != ("Bolt", "/admin/shop/product/1/change/")
    assert Link("Bolt", HREF) != Link("Bolt", "/admin/shop/product/1/change/")


def test_a_different_text_is_a_different_link():
    assert Link("Bolt", HREF) != ("Nut", HREF)
    assert Link("Bolt", HREF) != Link("Nut", HREF)


def test_a_link_is_never_its_text_alone():
    """The text is `value`'s business; a link is the pair."""
    assert Link("Bolt", HREF) != "Bolt"
    assert Link("Bolt", HREF) != ("Bolt",)


def test_the_href_is_split_into_its_parts():
    link = Link("Bolt", HREF)

    assert link.href.path == "/admin/shop/product/1/change/"
    assert link.href.query == "_changelist_filters=is_active__exact%3D1"
    assert link.href.geturl() == HREF


def test_a_list_of_links_compares_to_a_list_of_pairs():
    links = [Link("Datasheet", "/media/datasheet.pdf"), Link("Manual", "/media/manual.pdf")]

    assert links == [("Datasheet", "/media/datasheet.pdf"), ("Manual", "/media/manual.pdf")]
    assert links == [["Datasheet", "/media/datasheet.pdf"], ["Manual", "/media/manual.pdf"]]
    assert links != [("Manual", "/media/manual.pdf"), ("Datasheet", "/media/datasheet.pdf")]
    assert ("Manual", "/media/manual.pdf") in links
    assert ["Manual", "/media/manual.pdf"] in links


def test_a_link_shows_its_href_as_rendered():
    assert repr(Link("Bolt", HREF)) == f"Link('Bolt', {HREF!r})"
