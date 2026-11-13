from decimal import Decimal

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.validators import RegexValidator
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Category, Feed, Product
from .widgets import Shelf, SwatchPicker

# A message level between Django's warning (30) and error (40), with no tag of its own.
REFRESHED = 35


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
        # Two rules a SKU can break at once, so a field has more than one error.
        if "sku" in self.fields:
            self.fields["sku"].validators = [
                *self.fields["sku"].validators,
                RegexValidator(r"^SKU-", 'A SKU must start with "SKU-".'),
                RegexValidator(r"\s", "A SKU must not contain spaces.", inverse_match=True),
            ]

    # A rule about two fields together, so the form has an error that belongs to no
    # single field.
    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("featured") and not cleaned_data.get("is_active"):
            raise forms.ValidationError("A featured product must be active.")
        return cleaned_data


class StockFilter(admin.SimpleListFilter):
    """A filter of the project's own, named after a parameter that is no field's."""

    title = "stock level"
    parameter_name = "stock"

    def lookups(self, request, model_admin):
        return ("low", "Low"), ("high", "High")

    def queryset(self, request, queryset):
        if self.value() == "low":
            return queryset.filter(quantity__lt=5)
        if self.value() == "high":
            return queryset.filter(quantity__gte=5)
        return queryset


class StatusFilter(admin.SimpleListFilter):
    """A filter of the project's own without "All", as a filter that always has a value is
    often written, so every one of its links sends its parameter. `ProductAdmin` doesn't
    list it; the tests that need it do."""

    title = "status"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return ("active", "Active"), ("inactive", "Inactive")

    def choices(self, changelist):
        for lookup, title in self.lookup_choices:
            yield {
                "selected": self.value() == lookup,
                "query_string": changelist.get_query_string({self.parameter_name: lookup}),
                "display": title,
            }

    def queryset(self, request, queryset):
        if self.value() == "active":
            return queryset.filter(is_active=True)
        if self.value() == "inactive":
            return queryset.filter(is_active=False)
        return queryset


class PriceRangeFilter(admin.FieldListFilter):
    """A filter of the project's own on a field, whose links each send two parameters, the
    way a date filter's do. `ProductAdmin` doesn't list it; the tests that need it do."""

    bands = (("Under 10", "0", "10"), ("10 to 100", "10", "100"))

    def __init__(self, field, request, params, model, model_admin, field_path):
        self.since = f"{field_path}__gte"
        self.until = f"{field_path}__lt"
        super().__init__(field, request, params, model, model_admin, field_path)

    def expected_parameters(self):
        return [self.since, self.until]

    def choices(self, changelist):
        # From Django 5.0 a parameter's value is the list of the values sent for it.
        used = {
            name: value[-1] if isinstance(value, list) else value
            for name, value in self.used_parameters.items()
        }
        yield {
            "selected": not used,
            "query_string": changelist.get_query_string(remove=[self.since, self.until]),
            "display": "All",
        }
        for label, since, until in self.bands:
            band = {self.since: since, self.until: until}
            yield {
                "selected": used == band,
                "query_string": changelist.get_query_string(band),
                "display": label,
            }


class PriceInputFilter(PriceRangeFilter):
    """The same filter drawn as two inputs and a button, as range filters often are, so it
    has no links to pick from."""

    template = "shop/price_input_filter.html"


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
    # A boolean, a date, a relation and a filter of the project's own.
    list_filter = ("is_active", "released_on", "category", StockFilter)
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


# An admin that copies a record: its edit page offers "Save as new" in place of "Save and
# add another". Its edit page also has a button of the project's own, "Refresh", added by
# the feed's `submit_line.html`.
@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    save_as = True
    # A field with choices, a date-time and a time, each read by a rule of its own, a method
    # the admin draws as a boolean icon, and one with an empty value of its own.
    list_display = (
        "source",
        "mode",
        "refreshed_at",
        "refresh_time",
        "refreshed",
        "last_refreshed",
    )
    # Fieldsets with a name and without, with a description and without, holding the
    # fields in the order the admin would show them anyway. A name marked safe keeps its
    # markup, as a description does. The schedule starts collapsed.
    fieldsets = (
        (None, {"fields": ("source", "mode", "section", "categories")}),
        (
            "Schedule",
            {
                "classes": ("collapse",),
                "description": "When the feed last ran, and the time it runs <em>each day</em>.",
                "fields": ("refreshed_at", "refresh_time"),
            },
        ),
        (mark_safe("Appearance <em>on the page</em>"), {"fields": ("color",)}),
    )
    radio_fields = {"mode": admin.HORIZONTAL, "section": admin.VERTICAL}  # noqa: RUF012

    # The color is picked with a widget of the project's own, which the package does not
    # know.
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "color":
            kwargs["widget"] = SwatchPicker
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    # A feed that has been refreshed keeps its mode, so one field is read-only on some edit
    # pages and editable on others, through the admin's code rather than its settings.
    def get_readonly_fields(self, request, obj=None):
        if obj is not None and obj.refreshed_at is not None:
            return ("mode",)
        return super().get_readonly_fields(request, obj)

    @admin.display(boolean=True, description="Refreshed")
    def refreshed(self, feed):
        return feed.refreshed_at is not None

    @admin.display(description="Last refreshed", empty_value="never")
    def last_refreshed(self, feed):
        return feed.refreshed_at

    # Messages of the project's own next to the admin's. A source like "new feed.txt" gets
    # both warnings and then the admin's success message: several messages of one level,
    # and several levels, on one page. Each warning carries an extra tag, which is not part
    # of its level; the second one's is "info", which happens to be the name of a level.
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not obj.source.endswith(".csv"):
            self.message_user(
                request, "The source should be a CSV file.", messages.WARNING, extra_tags="source"
            )
        if " " in obj.source:
            self.message_user(
                request,
                "The source should not contain spaces.",
                messages.WARNING,
                extra_tags="info",
            )

    # "Refresh" saves as usual, then shows the feed's history rather than the changelist a
    # plain save leads to, so a test sees that this code answered it. It says so at level
    # 35, which Django has no tag for, so the message has no level until a project adds one.
    def response_change(self, request, obj):
        if "_refresh" in request.POST:
            self.message_user(request, "The feed was refreshed.", REFRESHED)
            return HttpResponseRedirect(
                reverse("admin:shop_feed_history", args=[obj.pk], current_app=self.admin_site.name)
            )
        return super().response_change(request, obj)


class CategoryForm(forms.ModelForm):
    # A form-only field drawn as two inputs by a widget of the project's own, so the suite
    # has a control no built-in widget class recognizes. Not required, so saving a
    # category is unchanged.
    shelf = forms.CharField(widget=Shelf, required=False)
    # A form-only field drawn as `filter_horizontal` draws one, which the admin's script
    # turns into two lists. Not required either.
    see_also = forms.ModelMultipleChoiceField(
        Category.objects.all(),
        required=False,
        widget=FilteredSelectMultiple("see also", is_stacked=False),
    )

    class Meta:
        model = Category
        fields = "__all__"


# A changelist whose rows link to nothing, so the suite has one without a change link.
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    form = CategoryForm
    list_display = ("name",)
    list_display_links = None
    # The shelf in a collapsed fieldset, so a fill that fails can be seen to leave it
    # collapsed.
    fieldsets = (
        (None, {"fields": ("name", "see_also")}),
        ("Placement", {"classes": ("collapse",), "fields": ("shelf",)}),
    )
