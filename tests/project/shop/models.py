from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=100)
    # Help on a field that shares its line with the price, which has none.
    sku = models.CharField(max_length=32, unique=True, help_text="The code printed on the label.")
    price = models.DecimalField(max_digits=8, decimal_places=2)
    # A number with a default, so the add page starts with a value in a number input. Its
    # help has markup, which the admin renders as is.
    quantity = models.PositiveIntegerField(
        default=1, help_text="How many are in stock, counted <em>at the warehouse</em>."
    )
    is_active = models.BooleanField(
        default=True, help_text="Only active products are listed in the shop."
    )
    featured = models.BooleanField(null=True, blank=True)
    released_on = models.DateField(null=True, blank=True)
    # A foreign key the form shows as a select with a blank option, and a change page
    # for a viewer renders as a link. It protects its category, so a category a product
    # uses has a delete confirmation with nothing to confirm.
    category = models.ForeignKey("Category", null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class Review(models.Model):
    """What a product takes with it when it is deleted, so its delete confirmation lists
    related objects. Not registered with the admin, so the confirmation shows its entries
    without a link, next to the product's, which has one."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    text = models.CharField(max_length=100)

    class Meta:
        ordering = ("pk",)

    def __str__(self):
        return self.text


class Feed(models.Model):
    """A model whose own fields are named after the arguments `populate` takes, so the
    suite proves a project is not kept from filling them.

    Its admin copies records and has a button of its own, so it also stands for an admin
    that offers "Save as new" and for one that adds an action to the form."""

    source = models.CharField(max_length=100)
    mode = models.CharField(
        max_length=20,
        choices=(("append", "Append"), ("replace", "Replace")),
        default="append",
    )
    # Drawn as radio buttons, as the mode is. It may be empty, so the admin adds a blank
    # option, and its options stand for objects rather than text.
    section = models.ForeignKey("Category", null=True, blank=True, on_delete=models.SET_NULL)
    # Drawn as a multiple select. Named on the category side, which the section already
    # takes the default name on.
    categories = models.ManyToManyField("Category", blank=True, related_name="feeds")
    # A date-time and a time, so a changelist shows each next to the product's dates.
    refreshed_at = models.DateTimeField(null=True, blank=True)
    refresh_time = models.TimeField(null=True, blank=True)
    # "red", "green" or "blue", picked with a widget of the project's own.
    color = models.CharField(max_length=10, blank=True, default="")

    def __str__(self):
        return self.source


class Category(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Manual(models.Model):
    """A model with a file, so the suite reads and fills the admin's file input. The file is
    required, so an edit page shows the stored one without a way to clear it, and the title
    is too, so leaving it empty gets a form rejected. The cover is an optional image, so an
    edit page offers to clear it, and image fields are shown to work like file fields."""

    title = models.CharField(max_length=100)
    file = models.FileField(upload_to="manuals/")
    cover = models.ImageField(upload_to="covers/", blank=True)

    def __str__(self):
        return self.title


class Bundle(models.Model):
    """A model with the admin's relational controls. Its categories are drawn as two lists
    side by side and its sections as two lists stacked, both by the admin's script. Its lead
    and add-ons are searched for in autocomplete boxes. Its relations are hidden on the other
    side, so the models they point at stay as they were."""

    name = models.CharField(max_length=100)
    categories = models.ManyToManyField(Category, blank=True, related_name="+")
    sections = models.ManyToManyField(Category, blank=True, related_name="+")
    lead = models.ForeignKey(
        Product, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    add_ons = models.ManyToManyField(Product, blank=True, related_name="+")

    def __str__(self):
        return self.name
