"""A widget of the project's own, which the package has no widget class for."""

from django import forms


class SwatchPicker(forms.Widget):
    """A hidden input holding the color, and a button for each color; the one chosen
    is pressed."""

    template_name = "shop/widgets/swatch_picker.html"
    colors = ("red", "green", "blue")

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["colors"] = self.colors
        return context


class Shelf(forms.MultiWidget):
    """Two text inputs for one value, the aisle and the shelf, drawn without the admin's
    markup for a date-time."""

    def __init__(self, attrs=None):
        super().__init__([forms.TextInput, forms.TextInput], attrs)

    def decompress(self, value):
        return value or [None, None]
