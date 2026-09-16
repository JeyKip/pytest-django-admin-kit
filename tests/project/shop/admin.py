from decimal import Decimal

from django.contrib import admin

from .models import Product


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

    # A released product stays on record. This gives the suite one page whose answer
    # depends on the object, not only on the user.
    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.released_on is not None:
            return False
        return super().has_delete_permission(request, obj)
