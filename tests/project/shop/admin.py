from decimal import Decimal

from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "price", "is_active", "released_on", "price_with_tax")
    list_filter = ("is_active",)
    search_fields = ("name", "sku")

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
