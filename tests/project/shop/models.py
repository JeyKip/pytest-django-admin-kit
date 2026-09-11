from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=100)
    sku = models.CharField(max_length=32, unique=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)
    released_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name
