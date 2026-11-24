"""The popups the admin opens from a field to add or change a related object: pages read,
filled and saved as any other, which close once saved and leave the object in the field."""

import datetime

import pytest

from project.shop.admin import BundleAdmin
from project.shop.models import Bundle, Category, Product

CLOSED = (
    "The popup is closed, so there is nothing to read from it. Read the page it was opened from."
)

# The admin draws icons next to the autocomplete box `lead`, and none next to the raw-ID
# input `replacement`.
COLLAPSED_PRODUCTS = (
    (None, {"fields": ("name",)}),
    ("Products", {"classes": ("collapse",), "fields": ("lead", "replacement")}),
)

# Makes every popup stay open for a short time after its page asks to close it.
CLOSE_LATE = """
const close = window.close.bind(window);
window.close = () => { setTimeout(close, 300); };
"""

PRODUCT = {
    "name": "Bolt",
    "sku": "SKU-Bolt",
    "price": "10.00",
    "released_on": datetime.date(2026, 1, 15),
}


def choice(instance):
    return str(instance.pk), instance.name


def test_add_related_opens_the_create_page_of_the_related_model(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Product)

    popup = page.fields["category"].add_related()

    assert popup.works
    assert popup.status_code == 200
    assert popup.destination == admin_ui.url.create(Category)
    assert set(popup.fields) == {"name", "see_also", "shelf"}
    assert popup.native is not page.native


def test_a_saved_popup_closes_and_chooses_the_object_added(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Product)
    popup = page.fields["category"].add_related()
    popup.populate(name="Toys")

    result = popup.save()

    assert result.success
    assert result.page is page
    assert not result.redirected_to_list(Category)
    assert popup.native.is_closed()
    assert page.fields["category"].value == choice(Category.objects.get(name="Toys"))


def test_a_save_waits_for_a_popup_that_closes_late(admin_ui, superuser):
    admin_ui.native.add_init_script(CLOSE_LATE)
    admin_ui.login(superuser)
    page = admin_ui.create(Product)
    popup = page.fields["category"].add_related()
    popup.populate(name="Toys")

    result = popup.save()

    assert result.success
    assert result.page is page
    assert popup.native.is_closed()
    assert page.fields["category"].value == choice(Category.objects.get(name="Toys"))


def test_the_object_added_is_stored_with_the_form(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Product)
    page.populate(PRODUCT)
    popup = page.fields["category"].add_related()
    popup.populate(name="Toys")
    popup.save()

    assert page.save().success

    assert Product.objects.get().category == Category.objects.get(name="Toys")


def test_change_related_opens_the_edit_page_of_the_object_chosen(
    admin_ui, superuser, released, category
):
    admin_ui.login(superuser)
    page = admin_ui.edit(released)

    popup = page.fields["category"].change_related()

    assert popup.works
    assert popup.destination == admin_ui.url.edit(category)
    assert popup.fields["name"].value == "Tools"


def test_change_related_follows_the_object_a_fill_chose(admin_ui, superuser, released):
    toys = Category.objects.create(name="Toys")
    admin_ui.login(superuser)
    page = admin_ui.edit(released)
    page.fields["category"].fill(toys)

    popup = page.fields["category"].change_related()

    assert popup.destination == admin_ui.url.edit(toys)


def test_a_saved_popup_closes_and_shows_the_new_label(admin_ui, superuser, released, category):
    admin_ui.login(superuser)
    page = admin_ui.edit(released)
    popup = page.fields["category"].change_related()
    popup.fields["name"].fill("Hand tools")

    result = popup.save()

    assert result.success
    assert result.page is page
    assert popup.native.is_closed()
    assert page.fields["category"].value == (str(category.pk), "Hand tools")


def test_a_rejected_popup_stays_open_with_its_errors(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Product)
    popup = page.fields["category"].add_related()

    result = popup.save()

    assert not result.success
    assert result.page is popup
    assert not popup.native.is_closed()
    assert popup.fields["name"].errors == ["This field is required."]
    assert page.fields["category"].value.value == ""


def test_a_rejected_popup_closes_once_corrected_and_saved(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Product)
    popup = page.fields["category"].add_related()
    popup.save()
    popup.fields["name"].fill("Toys")

    assert popup.save().success

    assert page.fields["category"].value == choice(Category.objects.get(name="Toys"))


@pytest.mark.parametrize(
    "read",
    [
        lambda popup: popup.fields,
        lambda popup: popup.status_code,
        lambda popup: popup.messages,
        lambda popup: popup.save(),
    ],
    ids=["fields", "status code", "messages", "save"],
)
def test_a_closed_popup_fails_at_once(admin_ui, superuser, read):
    admin_ui.login(superuser)
    popup = admin_ui.create(Product).fields["category"].add_related()
    popup.native.close()

    with pytest.raises(LookupError) as failure:
        read(popup)

    assert str(failure.value) == CLOSED


def test_a_field_read_after_its_popup_closed_fails_at_once(admin_ui, superuser):
    admin_ui.login(superuser)
    popup = admin_ui.create(Product).fields["category"].add_related()
    name = popup.fields["name"]
    popup.native.close()

    with pytest.raises(LookupError) as failure:
        _ = name.value

    assert str(failure.value) == CLOSED


def test_an_object_added_to_two_lists_is_in_the_chosen_one(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)
    popup = page.fields["categories"].add_related()
    popup.populate(name="Toys")

    assert popup.save().success

    assert page.fields["categories"].value == [choice(Category.objects.get(name="Toys"))]


def test_an_object_added_to_an_autocomplete_box_is_chosen(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)
    popup = page.fields["lead"].add_related()
    popup.populate(PRODUCT)

    assert popup.save().success

    assert page.fields["lead"].value == choice(Product.objects.get())


def test_a_popup_opens_a_popup_of_its_own(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)
    product = page.fields["lead"].add_related()
    product.populate(PRODUCT)
    category = product.fields["category"].add_related()
    category.populate(name="Toys")

    result = category.save()

    assert result.page is product
    assert product.fields["category"].value == choice(Category.objects.get(name="Toys"))
    assert product.save().page is page
    assert page.fields["lead"].value == choice(Product.objects.get())


def test_add_related_opens_a_collapsed_fieldset(admin_ui, superuser, monkeypatch):
    monkeypatch.setattr(BundleAdmin, "fieldsets", COLLAPSED_PRODUCTS)
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)

    popup = page.fields["lead"].add_related()

    assert popup.works
    assert not page.fieldsets[1].collapsed


def test_change_related_opens_a_collapsed_fieldset(admin_ui, superuser, product, monkeypatch):
    monkeypatch.setattr(BundleAdmin, "fieldsets", COLLAPSED_PRODUCTS)
    bundle = Bundle.objects.create(name="Starter kit", lead=product)
    admin_ui.login(superuser)
    page = admin_ui.edit(bundle)

    popup = page.fields["lead"].change_related()

    assert popup.works
    assert not page.fieldsets[1].collapsed


@pytest.mark.parametrize(
    "fail",
    [
        lambda page: page.fields["replacement"].add_related(),
        lambda page: page.fields["replacement"].change_related(),
        lambda page: page.fields["lead"].change_related(),
    ],
    ids=["nothing to add with", "nothing to change with", "nothing chosen"],
)
def test_a_popup_that_cannot_open_leaves_a_fieldset_collapsed(
    admin_ui, superuser, monkeypatch, fail
):
    monkeypatch.setattr(BundleAdmin, "fieldsets", COLLAPSED_PRODUCTS)
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)

    with pytest.raises(LookupError):
        fail(page)

    assert page.fieldsets[1].collapsed


def test_a_popup_the_admin_refuses_says_so(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Product)
    admin_ui.logout()

    popup = page.fields["category"].add_related()

    assert popup.denied
    assert not popup.works


def test_a_user_who_may_not_add_related_objects_gets_no_popup(admin_ui, editor, product):
    admin_ui.login(editor)
    page = admin_ui.edit(product)

    with pytest.raises(LookupError) as failure:
        page.fields["category"].add_related()

    assert str(failure.value) == "The field 'category' offers no way to add a related object."


def test_a_user_who_may_not_change_related_objects_gets_no_popup(admin_ui, editor, released):
    admin_ui.login(editor)
    page = admin_ui.edit(released)

    with pytest.raises(LookupError) as failure:
        page.fields["category"].change_related()

    assert str(failure.value) == "The field 'category' offers no way to change a related object."


def test_change_related_needs_an_object_chosen(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Product)

    with pytest.raises(LookupError) as failure:
        page.fields["category"].change_related()

    assert str(failure.value) == "The field 'category' has no related object chosen to change."


def test_two_lists_offer_no_related_object_to_change(admin_ui, superuser):
    """The admin draws no pencil next to a field of several objects."""
    admin_ui.login(superuser)
    page = admin_ui.create(Bundle)

    with pytest.raises(LookupError) as failure:
        page.fields["categories"].change_related()

    assert str(failure.value) == (
        "The field 'categories' offers no way to change a related object."
    )
