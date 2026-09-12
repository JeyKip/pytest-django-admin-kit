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
