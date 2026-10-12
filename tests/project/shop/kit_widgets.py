"""The widget classes the suite teaches the package, one per widget of the project's own."""

from django_admin_kit.fields import FieldChoice


class SwatchPickerWidget:
    """The swatch picker, read as the color whose button is pressed and filled by
    pressing the button for a color."""

    def marker(self, field):
        return ".swatch-picker"

    def read(self, field):
        pressed = field.native.locator('button[aria-pressed="true"]')
        if not pressed.count():
            return None
        return FieldChoice(pressed.get_attribute("data-value"), pressed.inner_text())

    def fill(self, field, value):
        if value:
            button = field.native.locator(f'button[data-value="{value}"]')
            if button.get_attribute("aria-pressed") != "true":
                button.click()
            return
        # No color: pressing the chosen one again clears it.
        pressed = field.native.locator('button[aria-pressed="true"]')
        if pressed.count():
            pressed.click()


# Classes a setting can name that are no widget class.
class Unmarked:
    def read(self, field):
        return None


class Unread:
    def marker(self, field):
        return ".swatch-picker"


class Unfilled:
    def marker(self, field):
        return ".swatch-picker"

    def read(self, field):
        return None
