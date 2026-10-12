"""The widget classes the suite teaches the package, one per widget of the project's own."""

from django_admin_kit.fields import FieldChoice


class SwatchPickerWidget:
    """The swatch picker, read as the color whose button is pressed, filled by pressing
    the button for a color, and offering a choice for each button."""

    def marker(self, field):
        return ".swatch-picker"

    def read(self, field):
        pressed = self._pressed(field)
        if not pressed.count():
            return None
        return self._choice(pressed)

    def fill(self, field, value):
        if value:
            button = field.native.locator(f'button[data-value="{value}"]')
            if button.get_attribute("aria-pressed") != "true":
                button.click()
            return
        # No color: pressing the chosen one again clears it.
        pressed = self._pressed(field)
        if pressed.count():
            pressed.click()

    def choices(self, field):
        return [self._choice(button) for button in field.native.locator("button").all()]

    def _pressed(self, field):
        return field.native.locator('button[aria-pressed="true"]')

    def _choice(self, button):
        return FieldChoice(button.get_attribute("data-value"), button.inner_text())


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


class FixedChoices(SwatchPickerWidget):
    choices = ("red", "green", "blue")
