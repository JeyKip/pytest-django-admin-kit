from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=100)
    sku = models.CharField(max_length=32, unique=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    # A number with a default, so the add page starts with a value in a number input.
    quantity = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    featured = models.BooleanField(null=True, blank=True)
    released_on = models.DateField(null=True, blank=True)
    # A foreign key the form shows as a select with a blank option, and a change page
    # for a viewer renders as a link.
    category = models.ForeignKey("Category", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class Feed(models.Model):
    """A model whose own fields are named after the arguments `populate` takes, so the
    suite proves a project is not kept from filling them."""

    source = models.CharField(max_length=100)
    mode = models.CharField(
        max_length=20,
        choices=(("append", "Append"), ("replace", "Replace")),
        default="append",
    )

    def __str__(self):
        return self.source


class Category(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name
