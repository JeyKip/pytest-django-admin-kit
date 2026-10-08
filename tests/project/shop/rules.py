"""Rules the suite names in its settings in place of the package's defaults.

Each returns the name of the rule with what it read, so a test sees which rule read a value.
"""


def boolean(rendered):
    return ("boolean", rendered.native.locator("img").get_attribute("alt"))


def text(rendered):
    return ("text", rendered.text)


# Something a setting can name that is no rule at all.
NOT_A_RULE = "boolean"
