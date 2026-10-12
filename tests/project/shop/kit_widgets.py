"""The widget classes the suite teaches the package, one per widget of the project's own."""

from django_admin_kit.fields import FieldChoice


class SwatchPickerWidget:
    """The swatch picker, read as the color whose button is pressed."""

    def marker(self, field):
        return ".swatch-picker"

    def read(self, field):
        pressed = field.native.locator('button[aria-pressed="true"]')
        if not pressed.count():
            return None
        return FieldChoice(pressed.get_attribute("data-value"), pressed.inner_text())


# Classes a setting can name that are no widget class.
class Unmarked:
    def read(self, field):
        return None


class Unread:
    def marker(self, field):
        return ".swatch-picker"
