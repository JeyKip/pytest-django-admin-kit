from decimal import Decimal

from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Feed, Product


class ProductForm(forms.ModelForm):
    # A field the admin renders hidden: posted with the form, never shown, the way a
    # value a script or the view fills in is carried.
    source = forms.CharField(widget=forms.HiddenInput, required=False, initial="admin")

    class Meta:
        model = Product
        fields = "__all__"

    # The model lets the release date be blank; the form requires it. That gives the
    # suite a field whose requiredness only the rendered form can tell. Set here rather
    # than by redeclaring the field, so the admin's date widget stays. A user who may
    # only view gets a form with no fields at all, hence the check.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "released_on" in self.fields:
            self.fields["released_on"].required = True


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductForm
    list_display = (
        "name",
        "sku",
        "price",
        "is_active",
        "featured",
        "released_on",
        "is_released",
        "price_with_tax",
        "documents",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "sku")
    empty_value_display = "(none)"
    # A field every user gets rendered only, next to the ones an editor may fill, and
    # one named after a method rather than a model field.
    readonly_fields = ("price_with_tax",)
    # The sku and the price share a line, so the form has a line with several fields
    # on it as well as the usual one field per line.
    fields = (
        "name",
        ("sku", "price"),
        "quantity",
        "is_active",
        "featured",
        "released_on",
        "category",
        "source",
        "price_with_tax",
    )

    # A bool the admin renders as text, because the column does not ask for the
    # icon.
    @admin.display(description="Released")
    def is_released(self, product):
        return product.released_on is not None

    # A column that is no model field and cannot be sorted, so the suite has one the
    # admin renders differently from the rest. On the add page it sees a product with
    # no price yet, and shows the empty value the way the admin would for a field.
    @admin.display(description="Price with tax")
    def price_with_tax(self, product):
        if product.price is None:
            return self.get_empty_value_display()
        return product.price * Decimal("1.2")

    # A cell with more than one link, to files rather than admin pages.
    @admin.display(description="Documents")
    def documents(self, product):
        return format_html(
            '<a href="/media/{sku}/datasheet.pdf">Datasheet</a> '
            '<a href="/media/{sku}/manual.pdf">Manual</a>',
            sku=product.sku,
        )

    # A released product stays on record. This gives the suite one page whose answer
    # depends on the object, not only on the user.
    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.released_on is not None:
            return False
        return super().has_delete_permission(request, obj)


admin.site.register(Feed)


# A changelist whose rows link to nothing, so the suite has one without a change link.
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    list_display_links = None
