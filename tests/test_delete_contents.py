"""What a delete confirmation says the deletion will remove, or what keeps it from being
confirmed."""

import django
import pytest

from project.shop.models import Product, Review

# Django 6.0 quotes the object's name in the opening sentence with curly quotes; earlier
# versions quote it with straight double quotes when asking and single quotes when refusing.
CURLY = django.VERSION >= (6, 0)

# Everything the confirmation reads. Each fails on a page that did not open and on one the
# browser has left.
READERS = {
    "deletions": lambda page: page.deletions,
    "deletion_counts": lambda page: page.deletion_counts,
    "intro": lambda page: page.intro,
    "blockers": lambda page: page.blockers,
}


@pytest.fixture
def reviewed(product):
    """The product with two reviews, which deleting it takes with it."""
    Review.objects.create(product=product, text="Great")
    Review.objects.create(product=product, text="Fine")
    return product


@pytest.fixture
def protected(category, product):
    """A category the product uses, which the product protects from deletion. The product
    is not released, so the admin lists it as protected rather than as a kind the user may
    not delete."""
    product.category = category
    product.save()
    return category


@pytest.fixture
def deleting_product(admin_ui, superuser):
    """Opens the confirmation for deleting a product, once the test has set it up."""
    admin_ui.login(superuser)
    return admin_ui.delete


def test_an_object_nothing_depends_on_lists_only_itself(deleting_product, product):
    page = deleting_product(product)

    assert page.deletions == ["Product: Widget"]


def test_an_object_lists_what_it_takes_with_it_after_itself_in_order(deleting_product, reviewed):
    page = deleting_product(reviewed)

    assert page.deletions == ["Product: Widget", "Review: Great", "Review: Fine"]


def test_an_entry_reads_as_text_whether_or_not_the_admin_links_it(deleting_product, reviewed):
    """The product's model is registered, so its entry links to its change page; the
    reviews' is not, so theirs are plain text."""
    page = deleting_product(reviewed)

    assert page.native.locator("#content li > a").all_text_contents() == ["Widget"]
    assert page.deletions == ["Product: Widget", "Review: Great", "Review: Fine"]


def test_a_page_that_cannot_be_confirmed_lists_nothing_to_remove(admin_ui, superuser, protected):
    """The page lists the product that protects the category, which the deletion would not
    remove."""
    admin_ui.login(superuser)

    page = admin_ui.delete(protected)

    assert not page.can_confirm_deleting
    assert page.native.locator("#content li").all_text_contents() == ["Product: Widget"]
    assert page.deletions == []


def test_an_object_nothing_depends_on_counts_one_of_its_model(deleting_product, product):
    page = deleting_product(product)

    assert page.deletion_counts == {"Products": 1}


def test_related_objects_are_counted_by_model(deleting_product, reviewed):
    page = deleting_product(reviewed)

    assert page.deletion_counts == {"Products": 1, "Reviews": 2}


def test_a_model_the_deletion_removes_none_of_is_not_counted(deleting_product, product):
    page = deleting_product(product)
    counts = page.deletion_counts

    assert "Reviews" not in counts
    with pytest.raises(KeyError) as failure:
        counts["Reviews"]
    assert failure.value.args[0] == "The page counts no model 'Reviews'. Models: 'Products'."


def test_a_page_that_cannot_be_confirmed_counts_nothing(admin_ui, superuser, protected):
    admin_ui.login(superuser)
    counts = admin_ui.delete(protected).deletion_counts

    assert counts == {}
    with pytest.raises(KeyError) as failure:
        counts["Categories"]
    assert failure.value.args[0] == "The page counts no model 'Categories'. Models: none."


def test_a_page_that_can_be_confirmed_asks_to_confirm(deleting_product, product):
    page = deleting_product(product)

    name = "“Widget”" if CURLY else '"Widget"'
    assert page.intro == (
        f"Are you sure you want to delete the product {name}? "
        "All of the following related items will be deleted:"
    )


def test_a_protected_page_says_why_it_cannot_be_confirmed(admin_ui, superuser, protected):
    admin_ui.login(superuser)

    page = admin_ui.delete(protected)

    name = "“Tools”" if CURLY else "'Tools'"
    assert page.intro == (
        f"Deleting the category {name} would require deleting the following protected "
        "related objects:"
    )


def test_a_protected_object_lists_what_protects_it(admin_ui, superuser, protected):
    admin_ui.login(superuser)

    page = admin_ui.delete(protected)

    assert page.blockers == ["Product: Widget"]


def test_an_object_blocked_both_ways_lists_only_the_kind_the_user_may_not_delete(
    admin_ui, superuser, category, released
):
    """The released product protects the category, and the shop's rule keeps a released
    product on record, so the user may not delete it either. The admin lists only the kind,
    and the protected product is not on the page."""
    admin_ui.login(superuser)

    page = admin_ui.delete(category)

    name = "“Tools”" if CURLY else "'Tools'"
    assert not page.can_confirm_deleting
    assert page.blockers == ["product"]
    assert page.native.locator("#content li").all_text_contents() == ["product"]
    assert page.intro == (
        f"Deleting the category {name} would result in deleting related objects, but your "
        "account doesn't have permission to delete the following types of objects:"
    )


def test_a_page_blocked_by_a_kind_removes_nothing(admin_ui, superuser, category, released):
    admin_ui.login(superuser)

    page = admin_ui.delete(category)

    assert page.deletions == []
    assert page.deletion_counts == {}


def test_a_page_that_can_be_confirmed_has_no_blockers(deleting_product, reviewed):
    page = deleting_product(reviewed)

    assert page.blockers == []


@pytest.mark.parametrize("read", READERS.values(), ids=READERS.keys())
def test_a_refused_page_has_nothing_to_read(admin_ui, viewer, product, read):
    admin_ui.login(viewer)
    page = admin_ui.delete(product)

    with pytest.raises(LookupError) as failure:
        read(page)

    assert str(failure.value) == (
        "The page did not open, so there is nothing to read from it. "
        f"Status 403, at {admin_ui.url.delete(product)}."
    )


@pytest.mark.parametrize("read", READERS.values(), ids=READERS.keys())
def test_a_page_the_browser_left_fails_at_once_when_read(
    admin_ui, left_for, deleting_product, product, read
):
    page = deleting_product(product)
    page.confirm_deleting()

    with pytest.raises(LookupError) as failure:
        read(page)

    assert str(failure.value) == left_for(admin_ui.url.list(Product))
