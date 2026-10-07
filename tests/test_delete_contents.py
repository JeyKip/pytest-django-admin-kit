"""What a delete confirmation says the deletion will remove."""

import pytest

from project.shop.models import Product, Review


@pytest.fixture
def reviewed(product):
    """The product with two reviews, which deleting it takes with it."""
    Review.objects.create(product=product, text="Great")
    Review.objects.create(product=product, text="Fine")
    return product


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


def test_a_page_that_cannot_be_confirmed_lists_nothing_to_remove(
    admin_ui, superuser, category, product
):
    """The page lists the product that protects the category, which the deletion would not
    remove."""
    product.category = category
    product.save()
    admin_ui.login(superuser)

    page = admin_ui.delete(category)

    assert not page.can_confirm_deleting
    assert page.native.locator("#content li").all_text_contents() == ["Product: Widget"]
    assert page.deletions == []


def test_a_refused_page_has_no_deletions_to_read(admin_ui, viewer, product):
    admin_ui.login(viewer)
    page = admin_ui.delete(product)

    with pytest.raises(LookupError) as failure:
        bool(page.deletions)

    assert str(failure.value) == (
        "The page did not open, so there is nothing to read from it. "
        f"Status 403, at {admin_ui.url.delete(product)}."
    )


def test_the_deletions_fail_once_the_browser_has_left_the_page(
    admin_ui, left_for, deleting_product, product
):
    page = deleting_product(product)
    page.confirm_deleting()

    with pytest.raises(LookupError) as failure:
        bool(page.deletions)

    assert str(failure.value) == left_for(admin_ui.url.list(Product))
