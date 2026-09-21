# Form fields: which fields a create or edit page has, which are required, what they say

Implements specification §10 (Create Page Fields), §11 (Edit Page Fields), §12 (Required and
Optional Fields) and §13 (Field Metadata: labels, initial values, choices, rendered-only
fields, field order), and the lines of other sections without which those cannot be marked
done:

* §3.5, addressing a field by name, and §3.6, `page.fields["name"].required` and
  `page.fields["name"].native`;
* §30, the form-field failure text;
* §32 criteria 11 to 14.

## 1. Scope

Built:

* `page.fields` on the create page and the edit page: an ordered mapping from field name to
  `FormField`, in the order the admin presents the fields. `"name" in page.fields`,
  `set(page.fields)`, `list(page.fields)` and `page.fields["name"]` are plain Python. An
  unknown name raises `KeyError` naming it and listing the fields the form has. A page that
  did not open raises `LookupError` from `fields`, like every other reader.
* `FormField`: `name`, `native`, `required`, `editable`, `value`, `label`, `choices`, `links`.
* `FieldChoice(value, label)`: one option of a select, the type §25 lists under `FormField`.
  It compares equal to another `FieldChoice` and to a `(value, label)` pair, never to a bare
  string; both parts are read by name.
* `page.required_fields` and `page.optional_fields`: sets of names.
* `value` of an editable field: what the control holds right now, text-first. A text, number,
  date or textarea control reads as its text; a checkbox as `True`/`False`; a select as the
  `FieldChoice` chosen, so `field.value.value == str(tools.pk)` and
  `field.value.label == "Tools"`.
  On a create page that is the initial value (§13.2). A rendered-only field reads like a
  changelist cell: its text, or the boolean the admin drew as an icon, with `links` next to
  it (§13.4).
* `label`: the label the admin shows for the field, without the label suffix, in whatever
  language the page was rendered in.
* `choices`: the `FieldChoice` list of a select, blank option included, so `("", "---------")
  in field.choices` and `field.value in field.choices` are plain checks; `[]` for a field
  without options.
* A `RenderedValue` type behind both a changelist cell and a rendered-only field, so the two
  share the reading of text, icons and links without one being the other.
* Spec marks, README, tests, and additions to the test project: a `category` foreign key on
  `Product`, a rendered-only field and a form that disagrees with the model about what is
  required.

Out of scope:

* Fields that render several controls under one name: radio buttons (`radio_fields`), groups
  of checkboxes, multiple selects, split date-times. None is in the test project and none is
  in 1.0.0's scope. §33 names them so they are not forgotten. Their `value`
  fails on Playwright's strict-mode error and their `choices` is `[]` until a slice handles
  them; `native` reaches them today.
* Inline formsets (§33, 1.1.0). Their rows are outside the selector this plan uses, so they
  never show up as fields.
* Populating and submitting (§14 onwards). `value` is a plain property, not cached, so that it
  reads the current state once populating exists. The §13.4 sentence "never populated by
  section 14" gets its mark with §14.
* The §28.5 field handling hooks. `FormField` reads its control in one method, which is the
  place a hook table plugs into later.
* The related-object icons the admin puts next to a foreign key select (add, change, view,
  delete). They are inside the field's box, so `native` reaches them, and they are not in
  `links`, which reads a rendered-only value only.
* `FieldChoice` in changelist matching. `Link` and `FieldChoice` never equal each other and
  live in different properties, so their pair equalities do not meet here. Should a project's
  §28.3 `choice` rule one day put a `FieldChoice` into a cell's value, a pair pattern would
  still match it, but `matching._asks_for_links` would print the cell's links instead of its
  value in the failure text. That display heuristic is the §28.3 slice's to revisit.

No data fields are added or changed in any request or serializer, so the field validation
rules section of the plan format does not apply. The one model field added
(`Product.category`) is test project data; its rules are in decision 13.

## 2. Where the change goes

| Layer | File | What exists | What this adds |
|---|---|---|---|
| Page | `src/django_admin_kit/pages.py` | `ModelPage` keeping the model; `CreatePage`, `EditPage` as empty subclasses; `_shown()`, `_text()`, `_token()` | a `FormPage(ModelPage)` base with `fields`, `required_fields`, `optional_fields`; `CreatePage` and `EditPage` inherit it |
| Fields | `src/django_admin_kit/fields.py` (new) | | `FormField`, `Fields`, `FieldChoice` |
| Rendered values | `src/django_admin_kit/rendered.py` (new) | | `Link`, moved from `rows.py`; `RenderedValue` |
| Rows | `src/django_admin_kit/rows.py` | `Link`; `Cell(element, column)` with `native`, `text`, `value`, `links` | `Cell(RenderedValue)` keeps only `column`; `Link` imported from `rendered.py` |
| Normalization | `src/django_admin_kit/normalize.py` | rules take a `Cell` | rules take a `RenderedValue` |
| Test project | `tests/project/shop/models.py`, `admin.py`, `migrations/0001_initial.py` | `Product`, `Category`; `ProductAdmin` with `price_with_tax` as a list column | `Product.category`; `readonly_fields = ("price_with_tax",)`; a `ProductForm` that requires `released_on`; the migration regenerated |
| Suite fixtures | `tests/conftest.py` | `product`, `products` | a `category` fixture ("Tools") |

Reused as is: `_shown()` for the guard, `_text()` and `_token()` for reading, `normalize`
and `Link` for the rendered-only value and links, `conftest.py` users (`superuser`, `editor`,
`viewer`, `adder`) and `product`.

## 3. Markup and rendering facts the code depends on

Checked in `admin/includes/fieldset.html`, `admin/helpers.py`, `admin/base.html`,
`admin/widgets/related_widget_wrapper.html` and the admin's `forms.css` and `base.css` on
Django 3.2, 5.0, 5.2, 6.0 and 6.1, and by rendering the test project's add page and a
viewer's change page on 5.2:

1. The fieldsets of the main form are `form > div > fieldset.module`. Inline formsets sit
   next to them in `form > div > div.inline-group`, so the direct-child chain leaves them
   out. From Django 5.1 a collapsible fieldset wraps its rows in `details`, so rows are
   found as descendants (`fieldset.module .form-row`), never as children.
2. Every line of a fieldset is a `div.form-row`. It carries one `field-<name>` class per field
   on the line. A line with one field is that field's element. A line with several fields
   holds one `div.fieldBox.field-<name>` per field (with `flex-container` added from 5.0),
   and that box is the field's element.
3. A form field whose widget is a `HiddenInput` (`widget.is_hidden`) gets the class `hidden`
   on its row when it is alone on the line (`Fieldline.has_visible_field`) and on its box
   otherwise. `.hidden` is `display: none !important` in the admin's stylesheet. The class is
   set when the page renders and the admin's own scripts never change it. A collapsed
   fieldset (`classes=("collapse",)`) hides its fields another way, with a closed `details`
   or, before 5.1, a script; its fields carry no `hidden` class.
4. `<name>` is the form field's name for an editable field and, for a rendered-only field,
   the entry of `readonly_fields`: a model field name or a callable's `__name__`. A lambda in
   `readonly_fields` has no name and gets no `field-` class.
5. The label is `AdminField.label_tag()`: a `label` with class `required` when the form field
   is required, `vCheckboxLabel` for a checkbox, `inline` when not first on its line. From
   Django 6.0 a widget with `use_fieldset` (radios, multi-widgets) gets a `legend` with the
   same classes instead. A rendered-only field's label (`AdminReadonlyField.label_tag()`)
   carries no `required` class in any version. The admin shows a required field only by
   making its label bold (`label.required { font-weight: bold }`); there is no asterisk or
   other text in the label.
6. The label's text is the field's label followed by the form's `label_suffix`, which
   defaults to `gettext(":")` and is translated per language by Django's own catalogs (`":"`
   under `en`, `" :"` under `fr`, the untranslated `":"` where a catalog has no entry). A
   checkbox label has no suffix. A rendered-only label is `capfirst(label)` plus the suffix.
   The page says which language it was rendered in: `admin/base.html` sets `<html lang="...">`
   from the request's `LANGUAGE_CODE`.
7. An editable field renders its control(s) with `name="<name>"`; a rendered-only field
   renders `div.readonly` holding `AdminReadonlyField.contents()`: text, or the same boolean
   icon `<img alt="True|False|None">` the changelist uses, or for a foreign key
   `<a href=".../<pk>/change/">str(obj)</a>` and the admin's empty value display when unset.
8. A foreign key select is wrapped in `div.related-widget-wrapper` together with
   `a.related-widget-wrapper-link` icons for adding, changing, viewing and deleting the
   related object. The select itself is still the one element named after the field. Its
   first option, when the field is not required, is `<option value="">` labelled
   `---------` up to Django 6.0 and `- Select an option -` from 6.1 (`BLANK_CHOICE_LABEL`);
   the suite carries the label in a version-aware module constant, as `test_delete.py` does
   for the delete page's title.
9. A viewer (view permission only) gets every field rendered only. `readonly_fields` are
   rendered only for everyone, and, with no `fields` or `fieldsets` set, come after the
   form's fields, in the order declared.
10. On the test project's add page: `name`, `sku`, `price` carry `label.required`;
    `is_active` is a checked checkbox; `featured` is a `NullBooleanSelect` with options
    `unknown`/`true`/`false` labelled Unknown/Yes/No; `released_on` is a text input with
    class `vDateField` inside `p.date`. A date value renders as the first
    `DATE_INPUT_FORMATS` entry of the locale, `2026-01-15` under `en`; the viewer's
    rendered-only version shows `Jan. 15, 2026`.

## 4. Decisions

1. **A field is its box.** `FormField.native` is the field's element from fact 2: the
   `form-row` for a field alone on its line, the `fieldBox` otherwise. It is the one element
   every field has, editable or rendered only, with one control or several, and it is what
   Django itself names after the field. The control is one locator away
   (`field.native.locator("input")`).
2. **`fields` is a `dict` that explains a miss.** `Fields` subclasses `dict[str, FormField]`
   and overrides `__missing__` to raise `KeyError("The form has no field named 'colour'.
   Fields: 'name', 'sku', ...")`, mirroring the row's message. Everything the spec asks of
   the mapping (membership, `set()`, `list()`, order) is what a dict already does, so no
   `Mapping` implementation is written.
3. **Hidden fields are not fields.** A `form-row` or `fieldBox` with the class `hidden` is
   skipped, as is a row without a `field-` class (fact 4). What a hidden field is: a form
   field whose widget is `HiddenInput`, which a project gets by declaring
   `widget=forms.HiddenInput` on a `ModelForm` field or through `formfield_overrides`. It
   carries a value the form must post but the user must not see or edit: an id a script fills
   in, a token, a value fixed by the view. The admin still renders it inside the fieldset, in
   a row that its stylesheet hides. It has a label the user never sees, and it is posted with
   the form whatever the user does, so §14 need not fill it and §15's modes need not know it.
   The skip goes by Django's class, not by Playwright's `is_visible()`: the class is the
   admin's own statement that the field is hidden and it does not move, while visibility
   also changes with a collapsed fieldset (fact 3), whose fields the user can open and fill
   and which must stay in `page.fields`. A project's own script that shows and hides a row
   ("conditionally displayed fields", §33 1.3.0) is outside what the admin renders and is
   not read here. `page.native` reaches a hidden input when a test needs it.
4. **`required` is the label's word.** `"required"` in the class list of the field's first
   `label` or `legend`. That is what the admin shows the user (the bold label, fact 5), it
   reflects the form field after any `ModelForm` change, as §12 demands, and it is the same in
   every supported version. The control's `required` attribute is not used: it depends on the
   form's `use_required_attribute` and a widget can drop it.
5. **`editable` is the absence of `div.readonly`.** Nothing else distinguishes the two
   renderings, and a rendered-only field is never required (fact 5), so `required_fields`
   excludes it without a special case. `optional_fields` is "editable and not required", so a
   rendered-only field is in neither set and a viewer's edit page has both sets empty:
   there is nothing to fill.
6. **One `RenderedValue` behind a cell and a rendered-only field.** A new module
   `rendered.py` holds `Link` (moved from `rows.py`) and `RenderedValue(element)` with
   `native`, `text`, `value` and `links`, which is exactly what `Cell` does today minus the
   column. `Cell(RenderedValue)` adds `column`, so `rows.py` shrinks. `FormField` composes
   one: a rendered-only field builds `RenderedValue(readonly_div)` and reads `value` and
   `links` from it. Inheritance for the cell, because a cell is a rendered value; composition
   for the field, because a field has one among a label and other things. The two kinds can
   then grow apart (a cell gets its model field for §28.3 routing, a field its widget) without
   one carrying the other's details. `normalize`'s rules take a `RenderedValue`, which is all
   they ever read (`native` and `text`), and `Link` is imported from
   `django_admin_kit.rendered` by `matching.py`, the tests and the README. An editable
   field's `links` is `[]`: the related-object icons of fact 8 are controls, not a value.
7. **An editable value is text unless the control is not text.** The control is the element
   named after the field inside the box. A checkbox reads `is_checked()`; a select reads its
   `option:checked` as a `FieldChoice` (decision 8); every other control reads
   `input_value()`, which covers text, number, email, URL, date inputs and textareas. This
   is the text-first rule of §3.4 applied to a form: `price` on the edit page reads
   `"10.00"`, `released_on` reads `"2026-01-15"`, each as the page shows it.
8. **A chosen option is a `FieldChoice`, and it takes no side.** `FieldChoice(value, label)`
   holds the option's `value` attribute and its collapsed text. It equals another
   `FieldChoice` and a `(value, label)` pair as a tuple or a list, and nothing else: a bare
   `str` compares unequal, whether it is the value or the label, so `==` never has to say
   which of the two a string means. Each part is read by name: `field.value.value ==
   str(tools.pk)` is what the form posts and what §14 will fill by, `field.value.label ==
   "Tools"` is what the user reads, `field.value.value == ""` is the blank option. It is
   hashable and its repr is `FieldChoice('3', 'Tools')`, so a failing comparison shows both
   parts. This is the same shape as `Link` and its pair equality, and the name is the one
   §25 already lists.
9. **`label` is the label's text without the suffix, in the page's language.** The
   collapsed text of the field's first `label` or `legend`, with the trailing suffix removed
   when present. The suffix is `gettext(":")` evaluated under the language the page names in
   `<html lang>` (fact 6), through `django.utils.translation.override`, so the same rule
   holds for every language Django ships a catalog for and for a project's own translation
   of `":"`, whether the language came from `LANGUAGE_CODE`, `LocaleMiddleware` or a
   per-user preference. The checkbox label, which has no suffix, needs no special case. A
   project that passes its own `label_suffix` to the form keeps it in the label; nothing in
   the page says what it is.
10. **`choices` is what the select offers.** For a field whose control is a `select`, the
    `FieldChoice` list in document order, blank option included, so `("", "---------")` is
    the first entry of an optional foreign key and `field.value in field.choices` holds. Any
    other field, editable or not, has `[]`: a text input has no fixed set of options. Radio
    buttons and groups of checkboxes are out of scope and read `[]` too until §33's slice
    handles them.
11. **`required`, `editable`, `label` and `choices` are cached; `value` is not.** The first
    four do not change while the page is open. `value` is what the control holds now, and
    §14 will change it.
12. **`FormField.__repr__` is `FormField('email')`.** With it, `assert
    page.fields["email"].required` fails as `where False = FormField('email').required`,
    which names the field and the property; without it pytest prints an object address. §30
    is reworded to show that output, since its current block promises a text no plain value
    can carry.
13. **Test project additions.** Three, each for a behaviour the plan has to show:
    * `Product.category = ForeignKey(Category, null=True, blank=True, on_delete=SET_NULL)`,
      declared after `released_on`. Not required, nullable, no default; a plain single-value
      select, within §2.1. It gives the suite a select with a blank option (§13.3), a
      rendered-only foreign key that the admin renders as a link (§13.4), and a foreign key
      `value` on both kinds of page. It is not in `list_display`, so no changelist test
      changes; `0001_initial.py` is regenerated as before.
    * `readonly_fields = ("price_with_tax",)` gives every user's page one rendered-only field
      next to editable ones, and one named after a callable.
    * `ProductForm.__init__` sets `self.fields["released_on"].required = True`. The model
      declares `released_on` with `blank=True`, so the model says optional and the form says
      required: the one case §12 asks for, where the actual form and not the model decides.
      Django puts the `required` class on the label from the form field at render time, after
      `__init__` has run, so the package reads `required` as `True`, `required_fields` lists
      the field and §15's required mode will fill it. The change is made in `__init__` rather
      than by redeclaring `released_on = forms.DateField(required=True)` on the form, because a
      redeclared field replaces the one the admin builds and loses the admin's date widget;
      the tweak keeps the form as the admin renders it and flips only `required`. A side
      benefit: every later test that populates required fields has to type a date.

## 5. Commit plan

Each slice is one code commit after review; spec marks and README changes for a slice go in
its commit.

### F0: `RenderedValue`

Goal: the shared type of decision 6, with no behaviour change.

Files:

* `src/django_admin_kit/rendered.py` (new): `Link` moved verbatim; `RenderedValue(element)`
  with `native`, `text`, `value`, `links`, taken from `Cell`.
* `src/django_admin_kit/rows.py`: `Cell(RenderedValue)` with `__init__(element, column)` and
  `column`; imports `Link` from `.rendered`.
* `src/django_admin_kit/normalize.py`: `Rule = Callable[[RenderedValue], Any]`,
  `normalize(rendered)`; the "no rule answered" message no longer names a column.
* `src/django_admin_kit/matching.py`, `tests/test_links.py`, `tests/test_matching.py`,
  `tests/test_rows.py`, `README.md`: `Link` imported from `django_admin_kit.rendered`. The
  spec names no import path for it.

Consistency: a pure move; every existing test passes unchanged apart from the import line.

### F1: which fields the page has

Goal: `page.fields` on create and edit pages, with names, order, membership, the descriptive
`KeyError`, the `LookupError` guard and `native`.

Files:

* `src/django_admin_kit/fields.py` (new): `FormField(element, name)` with `name`, `native`,
  `__repr__`; `Fields(dict)` with `__missing__`.
* `src/django_admin_kit/pages.py`: `FormPage(ModelPage)` with `fields` as a `cached_property`:
  for each `form > div > fieldset.module .form-row` under `_shown()`, read the `field-`
  tokens; one token and the row is the element, several and each `.fieldBox` with a `field-`
  token is; skip `hidden` elements and rows without a token; build `Fields` in document
  order. `CreatePage(FormPage)`, `EditPage(FormPage)`.
* `tests/project/shop/models.py`: `Product.category`; `migrations/0001_initial.py`
  regenerated. `tests/project/shop/admin.py`: `readonly_fields = ("price_with_tax",)`, with
  `price_with_tax` answering `None` for the unsaved product the add page hands it; a
  `ProductForm` declaring `source = CharField(widget=HiddenInput, required=False)`, the
  hidden field decision 3 skips, set as `ProductAdmin.form` (F2 adds its `__init__`).
* `tests/test_fields.py` (new), with the expected field list as a module constant:
  superuser's add page lists `name, sku, price, is_active, featured, released_on, category,
  price_with_tax` in order; membership and subset; `page.fields["name"].name == "name"` and
  its repr; an editor's edit page lists the same; a viewer's edit page lists the same (all
  rendered only, still fields); `source` is on the page but not in `fields`; the unknown
  name's exact message; a viewer's add page (403) raises `LookupError` from `fields`;
  `native` is a `Locator` holding the `name` input and its label.
* `specification.md`: §10 done marks on every example and paragraph, including the new
  sentence on hidden fields; §3.5 the "on a form" bullet and `page.fields["email"]`; §3.6
  `page.fields["name"].native`; §13.5 the example.
* `README.md`: a "Reading form fields" entry, extended by the later slices.

Consistency: nothing else reads the new module; the new model field is nullable and not
shown on the changelist, so every existing fixture and row constant stands.

### F2: required and optional fields

Goal: `required`, `editable`, `page.required_fields`, `page.optional_fields`.

Files:

* `src/django_admin_kit/fields.py`: `required` (decision 4) and `editable` (decision 5), both
  `cached_property`.
* `src/django_admin_kit/pages.py`: `FormPage.required_fields` and `optional_fields` as
  properties returning `set[str]`.
* `tests/project/shop/admin.py`: `ProductForm.__init__` (decision 13), with a comment saying
  why the form disagrees with the model.
* `tests/test_fields.py`: `name` is required; `is_active` is not; `released_on` is required
  though the model allows blank (the §12 sentence); `price_with_tax` is not editable and the
  rest are; `required_fields == {"name", "sku", "price", "released_on"}`;
  `optional_fields == {"is_active", "featured", "category"}`; a viewer's edit page has both
  sets empty and no editable field.
* `specification.md`: §12 done marks including the `ModelForm` sentence; §3.6
  `page.fields["name"].required`; §13.4 `assert not field.editable` and the sentence on
  `required_fields`; §30 the form-field block (decision 12); §32 items 11 and 12.

Consistency: F1's fields keep their meaning; the form change alters no fixture, since the
suite creates products through the ORM.

### F3: the value a field holds

Goal: `value` on editable and rendered-only fields, which on a create page is the initial
value.

Files:

* `src/django_admin_kit/fields.py`: `FieldChoice` (decision 8); `value` (decisions 6 and 7).
* `src/django_admin_kit/rendered.py`: the whitespace-collapsing read becomes `text_of`, shared
  with the option label.
* `tests/project/shop/models.py`: `Product.quantity = PositiveIntegerField(default=1)`, so the
  add page has a number input with an initial value, as §13.2's example has; the migration is
  regenerated and the field joins `FIELDS` and `required_fields`.
* `tests/conftest.py`: `category` fixture, `Category(name="Tools")`.
* `tests/test_fields.py`, with a product that has `released_on=datetime.date(2026, 1, 15)`
  and the category: on an editor's edit page `name == "Widget"`, `price == "10.00"`,
  `is_active is True`, `featured == ("unknown", "Unknown")`, `featured.label == "Unknown"`,
  `category == (str(tools.pk), "Tools")`, `category.value == str(tools.pk)`,
  `category.label == "Tools"`, `released_on == "2026-01-15"`, `price_with_tax == "12.000"`;
  on a viewer's edit page `name == "Widget"`, `is_active is True`, `featured is None`,
  `category == "Tools"`, `released_on == "Jan. 15, 2026"`; a product without a category
  reads `("", "---------")` for the editor and `"(none)"` for the viewer; on the add page
  `name == ""` and `is_active is True` (the initial values of §13.2). One behaviour per test.
* `tests/test_choices.py` (new), browser-free like `test_links.py`: `FieldChoice` equals
  another with the same parts, a tuple pair and a list pair; it does not equal its value as
  a string, its label as a string, a pair with a different part or a differently typed pair;
  a list of them compares element-wise to a list of pairs; it hashes like its parts; its
  repr is `FieldChoice('3', 'Tools')`. One behaviour per test.
* `specification.md`: §11 done marks; §13.2 (its example already corrected to text by the
  plan commit); §13.3's paragraph on `FieldChoice` marked where `value` is concerned; §13.4
  `field.value == "1 January 2026"`.

Consistency: `value` is new; nothing else calls it.

### F4: the label

Goal: `label` (§13.1).

Files:

* `src/django_admin_kit/fields.py`: `label` (decision 9), `cached_property`; the page's
  language is read once per page (`html[lang]`) and handed to each field with its element.
  The suffix is collapsed the way the label's text is before the comparison, because French
  renders it as a non-breaking space and a colon and the collapse turns that into a plain
  space; the space left in front of it is dropped with the suffix. Of Django's locales only
  French and Traditional Chinese (`：`) change the suffix, so the test that the page's
  language wins over the test thread's activates `zh-hant` in the thread.
* `tests/test_fields.py`: `page.fields["released_on"].label == "Released on"` (suffix
  removed); `is_active` reads `"Is active"` (checkbox, no suffix to remove); a rendered-only
  `price_with_tax` reads `"Price with tax"`; the viewer's rendered-only `name` reads
  `"Name"`; with pytest-django's `settings` fixture setting `LANGUAGE_CODE = "fr"`, which
  the live server picks up because it shares the process's settings, the label `"Nom"`
  comes back without `" :"`, proving the suffix is read for the page's language and not
  assumed.
* `specification.md`: §13.1 done marks.

Consistency: additive.

### F5: the choices

Goal: `choices` (§13.3).

Files:

* `src/django_admin_kit/fields.py`: `choices` (decision 10), `cached_property`.
* `tests/test_fields.py`: `category` on the add page is
  `[("", "---------"), (str(tools.pk), "Tools")]`; `featured` is
  `[("unknown", "Unknown"), ("true", "Yes"), ("false", "No")]`; `(str(tools.pk), "Tools") in
  page.fields["category"].choices`; on the edit page `field.value in field.choices`; a text
  field has `[]`; a rendered-only field has `[]`.
* `specification.md`: §13.3 done marks; §32 item 13.

Consistency: additive.

### F6: links on a rendered-only field

Goal: `links` (§13.4, second half).

Files:

* `src/django_admin_kit/fields.py`: `links` (decision 6).
* `tests/test_fields.py`: the viewer's `category` has
  `links == [("Tools", admin_ui.url.edit(tools))]`; the editor's editable `category` has
  `[]`; the viewer's `name` has `[]`.
* `specification.md`: §13.4 the `links` example; §13 sections marked done apart from the
  §14 sentence; §32 item 14.

Consistency: additive; `Link` and its pair equality come from `rendered.py` unchanged.
