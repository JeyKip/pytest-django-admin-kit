from decimal import Decimal

from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
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

    # A bool the admin renders as text, because the column does not ask for the
    # icon.
    @admin.display(description="Released")
    def is_released(self, product):
        return product.released_on is not None

    # A column that is no model field and cannot be sorted, so the suite has one the
    # admin renders differently from the rest.
    @admin.display(description="Price with tax")
    def price_with_tax(self, product):
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


# A changelist whose rows link to nothing, so the suite has one without a change link.
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    list_display_links = None
