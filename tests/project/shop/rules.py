"""Rules the suite names in its settings in place of the package's defaults.

Each returns the name of the rule with what it read, so a test sees which rule read a value.
"""


def _tagged(kind):
    def rule(rendered):
        return kind, rendered.text

    rule.__name__ = kind
    return rule


def boolean(rendered):
    return "boolean", rendered.native.locator("img").get_attribute("alt")


date = _tagged("date")
datetime = _tagged("datetime")
time = _tagged("time")
number = _tagged("number")
choice = _tagged("choice")
text = _tagged("text")

# Something a setting can name that is no rule at all.
NOT_A_RULE = "boolean"
