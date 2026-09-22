# Form population: filling a create or edit page from a dictionary or an object

Implements specification §14 (Form Population: dictionary source, object source, keyword
values) and §15
(Population Modes: required, optional, all), and the lines of other sections that cannot be
marked done without them:

* §1, "automatic population of form fields";
* §13.4, "rendered-only fields are never populated by section 14";
* §26, the `page.populate(...)` lines of the required-field population example;
* §32 criteria 15 to 19.

## 1. Scope

Built:

* `page.populate(source, mode=PagePopulationMode.ALL, **values)` on the create page and
  the edit page.
  `source` is a dictionary, read by key, or any object, read by attribute; a Django model
  instance is an object like any other. A keyword adds a field the source lacks or overrides
  what the source has for it, and keywords alone are a source too:
  `page.populate(product, name="Renamed")`, `page.populate(name="Widget", price="1.00")`. A
  field neither has a value for is left as it is, and a key, attribute or keyword that names
  no field of the form is ignored: it populates nothing, and the test fails on what it
  asserts next.
* Three modes, the members of the enum `PagePopulationMode`: `REQUIRED`, `OPTIONAL` and
  `ALL`, with the plain strings `"required"`, `"optional"` and `"all"` accepted in their
  place. A mode picks which of the form's fields are looked up in the source; nothing else
  in the source matters, so the §26 example, a full data set with
  `PagePopulationMode.REQUIRED`, fills the required fields and ignores the rest.
* `FormField.fill(value)`: one value into one field, the way a user would put it there. A
  text, number, date or textarea control is filled with the value's text; a checkbox is
  checked or unchecked by the value's truth; a select is given one of its options. A test
  passes ordinary Python values, a `Decimal`, a `date`, a bool, a model instance, and the
  control decides how each is written. `populate` is a
  loop over `fill`, and a test that wants one field filled calls `fill` itself.
* Spec marks, README and tests. The test project has a control of every kind the package
  fills, so it does not change.

Out of scope:

* Submitting (§16 onwards) and the compact `admin_ui.create(Product, data)`. `populate`
  leaves the page where it is, with the values in the controls, for `submit` to post.
* Controls that render several inputs under one name (radio buttons, checkbox groups,
  multiple selects, split date-times) and file inputs; §33, 1.3.0. `fill` on one of them
  fails the way `value` does today, on Playwright's own error, and `native` reaches them.
* Related-object population (§33, 1.1.0): a model instance's foreign key is set by its
  primary key, which is one scalar; nothing is created, looked up or traversed.
* The §28.5 field handling hooks. `fill` picks the control in one place, the same way
  `value` does, which is where a hook table plugs into later.
* Filling a rendered-only field, in any mode: the spec says never. `fill` on one raises.

No request or serializer field is added or changed, so the plan format's field validation
rules do not apply as such. What does apply is what each kind of control accepts from
`fill`, in section 5.

## 2. Where the change goes

| Layer | File | What exists | What this adds |
|---|---|---|---|
| Page | `src/django_admin_kit/pages.py` | `FormPage` with `fields`, `required_fields`, `optional_fields` | `FormPage.populate(source, mode, **values)`; the enum `PagePopulationMode` |
| Fields | `src/django_admin_kit/fields.py` | `FormField` with `value` reading each kind of control through `_control(kind)`; `FieldChoice`; `Fields` with its `KeyError` | `FormField.fill(value)` |
| Suite fixtures | `tests/conftest.py` | `product`, `category` | `released`, moved from `tests/test_fields.py`, once a second module needs it |
| Tests | `tests/test_populate.py` (new) | | one module for `fill` and `populate` |

Reused as is: `FormField._control(kind)` to find the control, `FormField.choices` to check
an option exists before the browser is asked to pick it, `FormField.editable` and
`required` to build the mode's field set, `FormPage._shown()` through `fields` for the
guard on a page that did not open, the `superuser`, `editor`, `viewer`, `product`,
`category` fixtures.

## 3. Rendering facts the code depends on

Checked in Django's `forms/widgets.py` and `forms/models.py` on 3.2 and 5.2, and in
Playwright's locator API:

1. A checkbox is one `input[type="checkbox"]` named after the field; Playwright's
   `set_checked(bool)` clicks it only when its state has to change.
2. A select is one `select` named after the field; `select_option(value=...)` picks the
   option by its `value` attribute, and waits until the timeout when there is no such
   option. The foreign key select's related-object icons are outside the `select`.
3. Every other control the package reads (`input` of type text, number, and the admin's date
   input, and `textarea`) takes `fill(text)`, which clears it and types the text. A number
   input refuses text that is no number, with Playwright's own error.
4. `ModelChoiceField.prepare_value` renders a model instance as its `pk`, so the option value
   of a foreign key select is `str(instance.pk)`. A `to_field_name` other than the primary
   key is not in the test project and not handled.
5. `NullBooleanSelect` spells its options `"unknown"`, `"true"`, `"false"` (since Django
   3.1, so on every supported version) and renders `True`, `False` and `None` as those. Any
   other select renders a Python value with `str()`, so a `BooleanField` with explicit
   choices has options `"True"` and `"False"`.
6. `DATE_INPUT_FORMATS` always ends with the ISO formats, whatever the locale, so the text
   `str(date)` produces (`2026-01-15`) is accepted by every date input, and the same holds
   for times and datetimes.
7. Django renders a checkbox as checked unless the value is `False`, `None` or `""`
   (`widgets.boolean_check`), compared by identity, so `0` renders as checked. Python's
   `bool()` differs from that only for `0` and other falsy non-strings; decision 6 uses
   `bool()`.

## 4. Decisions

1. **`populate` lives on `FormPage`**, so the create and edit pages share it and a page that
   did not open raises `LookupError` from it, through `fields`. It returns `None`: the page
   is what the test holds, and it reads a field back through `page.fields[name].value`,
   which is a plain property and so reads the control as it is now.

2. **A dictionary is read by key, anything else by attribute, and keywords come first.**
   `collections.abc.Mapping` decides. An attribute is looked up with `getattr(source, name)`
   guarded by `hasattr`, so a `SimpleNamespace`, a model instance, a dataclass and a plain
   object all work; a name the source lacks is skipped, in either form. Only the form's own
   field names are ever looked up, so a model instance is asked for `name`, `sku`, `price`,
   `quantity`, `is_active`, `featured`, `released_on` and `category`, and never for `pk`,
   `id`, `_state` or `category_id`, which no form field is named after. `product.category`
   is therefore asked for and gives the related object, which decision 6 turns into
   `str(pk)` for the select. For each candidate field the keywords are asked first and the
   source second, so a keyword overrides the source and adds what it lacks; with no source,
   the keywords are all there is. The signature is
   `populate(self, source=None, mode=PagePopulationMode.ALL, /, **values)`: `source` and
   `mode` positional-only, so no name is reserved and a form field named `source` or `mode`
   is a keyword like any other. The price is that `mode="required"` spelled as a keyword is
   a value for a field named `mode`, which no form has, so it is ignored and every field is
   populated; the spec shows the positional spelling only,
   `page.populate(data, PagePopulationMode.REQUIRED)`.

3. **The form decides the candidates, the mode narrows them, the source fills them.** The
   candidates are the fields `page.fields` lists, so a hidden field is never touched and a
   rendered-only one never filled. `ALL` is every editable field, `REQUIRED` is
   `required_fields`, `OPTIONAL` is `optional_fields`. Fields are filled in the form's
   order, whatever order the source has. A candidate the source has no value for is left as
   the page rendered it, in every mode.

4. **The modes are an enum, and the default is `PagePopulationMode.ALL`**, since §14.1 calls
   `page.populate(data)` with no mode and expects every field it names filled.
   `class PagePopulationMode(str, Enum)` in `django_admin_kit.pages`, next to `populate`,
   the method that takes it, with `REQUIRED = "required"`, `OPTIONAL = "optional"`,
   `ALL = "all"`; the `str` mixin keeps `PagePopulationMode.ALL == "all"` true on Python
   3.8, where `StrEnum` does not exist. The name says what it is a mode of, so a later
   version that adds a mode of something else has a name left to use. `populate` converts
   what it is given with `PagePopulationMode(mode)`, so `PagePopulationMode.REQUIRED` and
   `"required"` are the same call, and the package itself never compares against a bare
   string. A string that is no mode fails on the enum's own `ValueError`,
   `'x' is not a valid PagePopulationMode`.

5. **`fill` is public on `FormField`.** §28.5 says a project teaches the package "how to read
   and how to fill" a field, so filling is a field's own operation, and a test that sets one
   field says `page.fields["name"].fill("Gadget")` rather than building a one-key dictionary.
   `fill` picks the control the way `value` does: checkbox, then select, then whatever else
   is named after the field. On a rendered-only field it raises `LookupError`, the
   package's word for "there is nothing here to do that with", saying the field is rendered
   only.

6. **What `fill` makes of a value, per control:**

   * a text-like control is filled with `str(value)`, and `None` with `""`. That is what
     Django renders for a `Decimal`, an `int` and a `date` (fact 6), so a model instance's
     `price`, `quantity` and `released_on` land as the form would show them;
   * a checkbox is set to `bool(value)`: `True` and `1` check it, `False`, `0`, `None` and
     `""` uncheck it. A string is truthy unless empty, as Python says, so `"false"` checks
     the box; the reader gives a checkbox back as a bool and a model instance holds one, so
     a string is never the natural value there;
   * a select is given the value of one of its options, as text: a `FieldChoice` is its
     `value`, `None` is `""` (the blank option), anything else is `str(value)`. A model
     instance is its `str(pk)` (fact 4), added in F3 where objects arrive. That is how
     Django spells every select's options but one: a foreign key select has `str(pk)` per
     object and the blank `""`, a `CharField(choices=...)` has the strings as given, a
     `BooleanField` with explicit choices has `"True"` and `"False"`. The exception is a
     model `BooleanField(null=True)`, the test project's `featured`: its form field is
     `NullBooleanField`, whose widget `NullBooleanSelect` renders exactly three options,
     `"unknown"` (Unknown), `"true"` (Yes) and `"false"` (No), and maps `True`, `False` and
     `None` onto them (fact 5). So `True` is `"true"` there and `"True"` anywhere else, and
     `None` is `"unknown"` there and `""` anywhere else. The package sees the page, not the
     form class, so it cannot ask which widget it is looking at, only which options exist.
     Hence the lookup is two-step: when no option has `str(value)` and the value is `True`,
     `False` or `None`, the `NullBooleanSelect` spelling is looked for instead; `True` tries
     `"True"` then `"true"`, `False` tries `"False"` then `"false"`, `None` tries `""` then
     `"unknown"`. Whichever the page has wins, and both are Django's own, so
     `populate(product)` lands `featured` as Unknown, Yes or No, `populate(data,
     featured=True)` reads as a test would write it, and `"true"` or a `FieldChoice` from
     `choices` still hit the first step. When neither spelling is an option, `ValueError`
     names the field, the value and the option values there are. The check is against
     `choices`, so the failure is immediate and named rather than Playwright's timeout.

7. **No change to the test project.** `Product` already has a text (`name`, `sku`), a number
   (`price`, `quantity`), a date (`released_on`), a checkbox (`is_active`), a nullable
   boolean select (`featured`), a foreign key select (`category`), a rendered-only field
   (`price_with_tax`) and a hidden one (`source`). The `released` fixture moves from
   `test_fields.py` to `conftest.py` in F3, when a second module needs a product with every
   field set.

8. **Tests read the page back.** Each test fills, then asserts `page.fields[name].value`,
   which goes through the existing readers; nothing is submitted. A test that proves a field
   was left alone asserts the value the page started with.

## 5. What each control accepts from `fill`

| Control | Accepted | Written as | Refused |
|---|---|---|---|
| text, number, date input; textarea | any value; `None` | `str(value)`; `""` | nothing by the package; a number input refuses non-numbers with Playwright's error |
| checkbox | any value | `set_checked(bool(value))` | nothing; a non-empty string checks it |
| select | `FieldChoice`, `str`, `None`, a model instance (F3), `bool` or `None` for a nullable boolean | `select_option(value=...)` with the option value of decision 6 | a value no option has, `ValueError` listing the option values |
| rendered-only field | nothing | | any call, `LookupError` |

## 6. Commit plan

Each slice is one code commit after review; spec marks and README changes for a slice go in
its commit.

### F1: filling one field

Goal: `FormField.fill(value)`, one value into one field, for every kind of control the
package fills.

Files:

* `src/django_admin_kit/fields.py`: `FormField.fill(value)` per decisions 5 and 6 without
  the model instance rule; a module-level helper for the select's option value, which F3
  extends.
* `tests/test_populate.py` (new): a text control is filled with the text; a number with a
  `Decimal` as its text; a date with a `datetime.date` as ISO text; `None` clears a text
  control; a checkbox is unchecked with `False` and checked again with `True`; a checkbox
  is set by the truth of a number, `0` unchecking and `1` checking; a select is given an
  option's value; a select is given a `FieldChoice` from its own `choices`; `None` picks
  the blank option; the nullable boolean select takes `True`, `False` and `None`; a value
  no option has raises the exact `ValueError` message; a rendered-only field raises
  `LookupError` with its message; a viewer's change page has no field to fill, so every
  field raises it.
* `specification.md`: the §14 intro sentence on `fill`, and the §13.4 sentence for
  rendered-only fields.
* `README.md`: a "Filling a form" entry, one field filled, extended by F2 to F4.

Consistency: nothing existing calls `fill`; `value` and `choices` are unchanged, so every
earlier test stands.

### F2: `populate` from a dictionary and from keywords

Goal: a page filled in one call, every editable field the dictionary or the keywords name.

Files:

* `src/django_admin_kit/pages.py`: `FormPage.populate(source=None, /, **values)` over every
  editable field, asking the keywords first and a `Mapping` by key second.
* `tests/test_populate.py`: a dictionary fills the fields it names and leaves the others as
  rendered; a key that names no field is ignored; a rendered-only field's key is ignored and
  the field keeps its value; keywords alone fill the fields they name; a keyword overrides
  the dictionary's value for the same field; a keyword adds a field the dictionary lacks; a
  keyword that names no field is ignored; a viewer's change page has nothing to fill, so a
  dictionary changes nothing; a page that did not open raises `LookupError` from `populate`.
* `specification.md`: §14 intro, §14.1 and §14.3 done marks.
* `README.md`: the `populate({...})` and keyword lines.

Consistency: `populate` is a loop over F1's `fill`, which no other code calls.

### F3: an object as the source

Goal: `populate(SimpleNamespace(...))`, `populate(product)` and any plain object.

Files:

* `src/django_admin_kit/pages.py`: the source lookup reads a non-mapping by attribute,
  `hasattr` then `getattr`.
* `src/django_admin_kit/fields.py`: the select's option value for a model instance is
  `str(instance.pk)`.
* `tests/conftest.py`: `released` moved here from `tests/test_fields.py`, unchanged.
* `tests/test_populate.py`: a `SimpleNamespace` fills the fields it has attributes for and
  skips the rest; an instance of a plain class written in the test, with attributes set in
  its `__init__`, fills the same way, and one with a field name as a property fills from
  what the property returns; a model instance fills the add page with every editable field,
  read back as `"Widget"`, `"SKU-1"`, `"10.00"`, `"1"`, `True`, `("unknown", "Unknown")`,
  `"2026-01-15"` and `(str(category.pk), "Tools")`; a model instance with nothing set for
  its nullable fields clears the date and picks the blank category; a dictionary may carry
  a model instance for a select too; a keyword overrides a model instance's attribute.
* `specification.md`: §14.2 done marks.
* `README.md`: the `populate(product)` line.

Consistency: a mapping still takes the F2 path; the attribute path only runs for what F2
had no rule for.

### F4: modes

Goal: the `PagePopulationMode` enum, the three modes, the error for anything else.

Files:

* `src/django_admin_kit/pages.py`: `PagePopulationMode`;
  `populate(source=None, mode=PagePopulationMode.ALL, /, **values)`, the mode picking the
  candidate set per decision 3, the conversion and its `ValueError` per decision 4.
* `tests/test_populate.py`: the §26 example on the test project, a full data set under
  `REQUIRED` fills `name`, `sku`, `price`, `quantity` and `released_on` and leaves
  `is_active`, `featured` and `category` as rendered; `OPTIONAL` the other way round; `ALL`
  is the default; the plain string `"required"` is the same call as `REQUIRED`; a mode that
  is none of the three raises `ValueError` with the enum's message.
* `specification.md`: §15 done marks; §1 bullet; §26 the `populate` lines; §32 items 15 to
  19.
* `README.md`: the `populate(data, PagePopulationMode.REQUIRED)` line.

Consistency: the default keeps F2's and F3's behaviour, so their tests stand as written.
