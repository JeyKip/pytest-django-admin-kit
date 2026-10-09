# Field handling hooks (spec section 28.5)

## What the section asks for

> A project must be able to teach the package how to read and how to fill a field
> representation the package does not know. Once registered, such a field participates in field
> inspection, population, and submission like any other.

It is also the open half of acceptance criterion 34 ("... and extend field handling from a
project, without subclassing package internals") and the last unticked item of section 28.1
("field handling").

## What the package does with a field today

A `FormField` is the box the admin draws around a label, a control and help text. Most of what a
test reads comes from that box and works for any widget:

| Read | Comes from | Depends on the widget? |
|---|---|---|
| `name`, `native` | the box's `field-<name>` class | no |
| `label` | the box's `label` or `legend` | no |
| `required` | the label's `required` class | no |
| `editable` | whether the box has `div.readonly` | no |
| `errors` | the box's `ul.errorlist` | no |
| `links` | rendered-only fields only | no |
| `value` | the control named after the field | **yes** |
| `fill(value)` | the control named after the field | **yes** |
| `choices` | the `select` named after the field | **yes** |

`value`, `fill` and `choices` know three kinds of control, each found by the field's name
(`src/django_admin_kit/fields.py:153-210`): a checkbox, a select, and anything else, which is
taken to be one input that holds text. `populate` (`src/django_admin_kit/pages.py:528`) calls
`fill` on every field in the mode, and the "rendered back after an invalid submission" check of
section 26 is `value`. So three methods decide whether a widget takes part in inspection,
population and submission.

A widget that is not one control named after its field breaks those three. I checked one in this
repository. `Feed.refreshed_at` is a `DateTimeField`, which the admin draws as two inputs,
`refreshed_at_0` and `refreshed_at_1`:

```
label, required, editable   -> 'Refreshed at', False, True     (fine)
value                       -> TimeoutError: Locator.input_value: Timeout exceeded
fill("2026-01-15 10:00")    -> TimeoutError: Locator.fill: Timeout exceeded
```

Each call waits out the whole timeout (30 seconds by default) and the error says nothing about
the field. Because `populate` fills every field the source has a value for,
`page.populate(feed)` on the feed's form fails the same way, even when `refreshed_at` is `None`.
A test that wants every other field filled from an instance has no way to leave that one out.

The other shapes fail like this, judging by the same code:

* **several controls under one name**, such as a group of radio buttons: the lookup matches
  several inputs, and the browser layer refuses with a strict mode violation;
* **a hidden input set by a script**, as most widgets built in JavaScript keep their value:
  `value` reads the hidden input and happens to work, but `fill` fails, because a hidden input
  cannot be typed into;
* **a select whose options come from the server**, as an autocomplete's do: the select holds
  only the chosen option, so `fill` reports that the field "offers no option" for anything else.

Section 3.6 already lets a test drive any of these through `field.native`. That covers one test
touching one widget. It does not let the field take part in `populate`, or in a contract a
project reuses across models (section 3.7). For that the package has to know the widget, and
28.5 is how a project tells it.

## Use cases

Each of these is a widget that real admins carry and that the package cannot read or fill today.

1. **A widget of the project's own.** A colour swatch picker, a star rating or a toggle switch:
   buttons drawn by the project that set a hidden input. A widget class reads the hidden input, fills
   by clicking the button for the value, and offers the buttons as choices. After that,
   `populate(product)` sets the colour like any other field.

2. **Rich text editors** (TinyMCE, CKEditor, Quill-based widgets). The textarea the form posts is
   hidden, and the text lives in an editor frame. A widget class fills by typing into the editor, so
   the editor's own sync runs as it does for a user, and reads the editor's content back.

3. **Code and JSON editors** (Ace, CodeMirror, JSON widgets). The same shape as rich text. A
   widget class can read the value as parsed JSON, so a test compares dictionaries rather than
   whitespace.

4. **Widgets of several inputs**: Django's `MultiWidget` family. That covers the admin's own
   split date-time (the `Feed.refreshed_at` failure above), an amount next to a currency, the
   postgres array and range widgets, and phone numbers split by country code. A widget class fills
   `<name>_0`, `<name>_1` from one value, such as a `datetime` or a `Money`, and reads them back
   as one. That alone makes `populate(feed)` work.

5. **Radio buttons** (`radio_fields`). The package's own support is planned for 1.3.0. Until
   then a widget class reads the checked one as a `FieldChoice`, offers every button's value and
   label as `choices`, and fills by checking one.

6. **Autocomplete** (the admin's `autocomplete_fields`, and the select2-based apps). A widget class
   types the value into the search box and picks the result, so a test fills a related object by
   name without knowing its primary key.

7. **Map and location widgets.** Hidden latitude and longitude inputs under a map. A widget class
   fills a `(lat, lng)` pair or a point object.

8. **A control the package already knows, read differently.** A project that wants the date
   inputs read as `date` objects, the way 28.3 lets it type a rendered date, subclasses
   `TextWidget` with a selector for `input.vDateField` and a `read` that parses. A select whose
   value should read as the bare value rather than a `FieldChoice` is a subclass of
   `SelectWidget` overriding `read`. The package's own controls are widget classes like the
   project's, behind them in the table, so this is the same mechanism as the rest.

What it is not for:

* rendered-only fields: their value is read by the normalization rules of 28.3, and a rule for a
  representation the package does not know is already on the Later list;
* pages of the project's own: those are helpers around `page.native` (28.6);
* a single test poking a widget once: `field.native` (3.6) is the shorter path.

## Scope

In scope:

* the package's three controls rewritten as public widget classes, `CheckboxWidget`,
  `SelectWidget` and `TextWidget`, in one ordered table that `FormField` asks;
* an immediate error for a field no widget class recognises, in place of the timeout;
* a `widgets` setting naming a project's widget classes by dotted path, validated loudly with the
  rest, and put in front of the package's own;
* a session fixture `admin_ui_widgets` built from it, overridable like `admin_ui_normalizers`;
* a widget of the test project's own, with its widget class, to prove all of the above end to end;
* README and spec.

Out of scope:

* rendered-only fields (28.3, and the Later item for new kinds);
* widget classes for Django's own widgets that the package does not handle yet (radio buttons,
  split date-times, multiple selects, files, autocomplete): these stay planned for 1.3.0, where
  each becomes one more built-in widget class. Until then a project writes its own;
* removing a built-in widget class from the table. A project puts its own in front instead;
* per-test or per-model tables;
* a widget class for a whole field box, label and errors included. Those are widget-agnostic
  already.

## Pipeline recap

| Layer | File | Change |
|---|---|---|
| Widget classes | `src/django_admin_kit/widgets.py` (new) | `CheckboxWidget`, `SelectWidget`, `TextWidget`; `Widgets(project=())` with `widget_for(field)` |
| Field | `src/django_admin_kit/fields.py` | `value`, `fill`, `choices` ask the table; the three control branches, `_option` and `_option_spellings` move out |
| Settings | `src/django_admin_kit/config.py` | `widgets` key, `_widgets()` validation, `Config.widgets` |
| Fixture | `src/django_admin_kit/plugin.py` | `admin_ui_widgets(admin_ui_config)`, passed into `AdminSession` |
| Plumbing | `session.py`, `pages.py` | `widgets` passed beside `normalizers` to `AdminPage`, `ModelPage`, `_page_at`, and into `FormField` from `FormPage.fields` |
| Test project | `tests/project/shop/` | `Feed.colour`, the swatch picker, its widget class |

Rows and cells need nothing: a changelist has no controls until `list_editable` (1.2.0).

## Decisions

1. **Words.** A *widget class* is the package's or the project's class that reads and fills one
   kind of control. A *widget* without "class" is what Django draws. The setting is `widgets`,
   since a widget class is about the control: the label, the errors and requiredness of a field
   stay the package's. The built-ins are named `CheckboxWidget`, `SelectWidget` and `TextWidget`.
   `TextWidget` rather than `TextInputWidget`, because it covers textareas, number and date
   inputs as well, and because Django's admin already has an `AdminTextInputWidget`.

2. **A widget class recognises its control by a selector it builds for the field.**
   `selector(field)` returns a CSS selector, and the first widget class whose selector matches
   something inside the field's box reads and fills the field. It is a method taking the field,
   because the package's own controls are known by the field's name; a project widget class with
   a fixed selector returns a constant. It is called `selector` rather than `get_selector`:
   Django spells a method `get_*` when it stands behind an attribute of the same name, and there
   is no attribute here, so `selector(field)` reads like the `read(field)`, `fill(field, value)`
   and `choices(field)` beside it.

   Matching reads the page, as everything else does (3.9), so it sees what a script drew as well
   as what the server sent. It needs no request to build the form, and one widget class serves
   every form the widget appears on. A line with several fields gives each its own box, so a
   selector never matches the neighbour's widget.

   **All selectors are tried in one browser call.** Each call into the browser costs a round
   trip: about 6 ms here, whether a selector matches or not and whatever the size of the box,
   which takes the browser microseconds to search. (Measured on the product form's `category`
   box, 14 elements: `count()` 5.8 ms with no match, 6.2 ms with one; `field.value` 34 ms for a
   text field today.) Asking each widget class's selector in turn would add 6 ms per project
   class to every `value` and `fill`, about 180 ms on a ten-field `populate` with three classes.
   So `widget_for` builds the selectors in Python and sends them in one call, which returns the
   position of the first that matches, or -1:

   ```python
   index = field.native.evaluate(
       "(box, selectors) => selectors.findIndex(s => box.querySelector(s))",
       [widget.selector(field) for widget in self._widgets],
   )
   ```

   That costs one round trip however many classes there are. Today a text field makes three
   (checkbox, select, `input_value`); with the table it makes two (the match, `input_value`). The
   price is that a selector is plain CSS as the browser's `querySelector` reads it, and the
   browser layer's own syntax, such as `text=` or `>>`, is not available. Where a widget class
   needs that, it uses it inside `read` and `fill`, which take locators as usual.

3. **The package's three controls are widget classes like any other**, last in the table, in the
   order the code tries them today:

   ```python
   class CheckboxWidget:
       def selector(self, field):
           return f'input[type="checkbox"][name="{field.name}"]'

       def read(self, field):
           return field.native.locator(self.selector(field)).is_checked()

       def fill(self, field, value):
           field.native.locator(self.selector(field)).set_checked(bool(value))


   class SelectWidget:
       def selector(self, field):
           return f'select[name="{field.name}"]'

       # read: the FieldChoice chosen; fill: the option standing for the value, by
       # `_option_spellings`; choices: the options in order, the blank one included.


   class TextWidget:
       """Whatever one control carries the field's name, holding text."""

       def selector(self, field):
           return f'[name="{field.name}"]'

       # read: the control's text; fill: the value's text, None emptying it.
   ```

   `FormField.value`, `fill` and `choices` each become "the widget class for this field, then its
   method", and the branches leave `fields.py`. `FieldChoice` stays in `fields.py`; `widgets.py`
   imports it, and `fields.py` imports `Widgets` only for type checking, so the two modules do not
   import each other at runtime. The built-ins are public, so a project may subclass one to change
   a single method. It never has to: no rule of 28.7 is broken.

   `TextWidget` also matches a hidden input and every button of a radio group. Both fail today in
   the same way, so nothing gets worse, but `TextWidget` must stay last.

4. **A widget of several components is one field with one widget class.** Django renders a whole
   widget inside its field's box, whatever it is made of, and the package lists fields by the
   box's `field-<name>` class, never by inputs. So the admin's split date-time is one field,
   `refreshed_at`, and never two fields `refreshed_at_0` and `refreshed_at_1`. The probe above
   showed exactly that. Four cases follow from this:

   * **Several inputs**, as in a `MultiWidget`: the selector needs to match only one thing that
     marks the widget, such as `p.datetime`. Matching several elements is fine, because the
     package only asks whether there is a match. The widget class then reaches each input by
     name through the box:

     ```python
     class SplitDateTimeWidget:
         def selector(self, field):
             return "p.datetime"

         def read(self, field):
             return tuple(self._part(field, i).input_value() for i in (0, 1))

         def fill(self, field, value):
             date, time = ("", "") if value is None else (f"{value:%Y-%m-%d}", f"{value:%H:%M:%S}")
             self._part(field, 0).fill(date)
             self._part(field, 1).fill(time)

         def _part(self, field, index):
             return field.native.locator(f'[name="{field.name}_{index}"]')
     ```

     `fill` takes one value, such as a `datetime`, and spreads it over the parts, so
     `populate(feed)` hands it the instance's attribute as it does for any field.
   * **Parts drawn outside the box.** An autocomplete's results list and the admin's calendar
     popup are appended to the page's `body`. The selector still matches what sits in the box;
     the widget class reaches the rest through `field.native.page`, the browser layer's own page.
   * **Parts in a frame.** A rich text editor's body is an `iframe` inside the box, reached with
     `field.native.frame_locator("iframe")`.
   * **One widget over several model fields**, such as a map that sets `latitude` and
     `longitude`. When the form draws them as two fields, they are two boxes, each filled on its
     own. When the form folds them into one form field, it is one box, and the case is the same
     as several inputs.

5. **The interface.** Every method takes the `FormField`, whose `native` is the box and `name` the
   field's name:

   ```python
   class SwatchPickerWidget:
       def selector(self, field):        # what marks the control inside the field's box
           return ".swatch-picker"

       def read(self, field):            # what `field.value` returns
           return field.native.locator("input[type=hidden]").input_value()

       def fill(self, field, value):     # what `field.fill(value)` and `populate` do
           field.native.locator(f'button[data-value="{value}"]').click()

       def choices(self, field):         # optional; `field.choices` is [] without it
           return [
               FieldChoice(button.get_attribute("data-value"), button.inner_text())
               for button in field.native.locator("button").all()
           ]
   ```

   `selector`, `read` and `fill` are required. `choices` is optional, because most widgets offer
   no fixed set; `CheckboxWidget` and `TextWidget` have none. A widget class returns whatever
   value suits it: the package passes it through untouched, as it does a normalization rule's
   result.

   A widget class must not use `field.value`, `field.fill` or `field.choices` of the same field,
   from any of its methods, `selector` included: that asks the table again and never ends. Nor
   should `selector` read the page, since it runs for every field on every read. The README says
   both.

6. **Order and replacing a built-in.** The table is the project's widget classes in the order
   listed, then `CheckboxWidget`, `SelectWidget`, `TextWidget`. A project replaces a built-in by
   listing a widget class that matches the same control, which then comes first. Nothing needs
   naming and nothing is restated, as with the rules of 28.3. A built-in cannot be removed, only
   put behind; no use case needs more.

7. **A field no widget class recognises is reported at once.** When no selector matches, `value`
   and `fill` raise `LookupError` naming the field and the setting, where today they wait out the
   timeout. `choices` keeps answering `[]`, as it does today for anything that is no select.
   Matching counts what the page holds without waiting, so a control a script adds after the page
   has loaded would be reported before it appears. Controls built on page load exist by the time
   the package reads, and the package already waits for its own navigations, so I think the risk
   is small.

8. **A widget class is named by dotted path; the package makes one instance of it with no
   arguments**, as Django does for `AUTHENTICATION_BACKENDS`. The path keeps project code out of
   the settings module, as for the site and the rules. A class lets a widget class keep helpers
   next to its methods.

   ```python
   DJANGO_ADMIN_KIT = {
       "widgets": [
           "tests.kit_widgets.SwatchPickerWidget",
       ],
   }
   ```

9. **Editable fields only.** `value` on a rendered-only field keeps going to the normalization
   rules, and `fill` on one keeps raising `LookupError`, before any widget class is asked. The
   section-13 split between controls and rendered values stays as it is.

10. **Configured project-wide, overridden by fixture.** `admin_ui_widgets` is a session fixture
    built from `admin_ui_config`, like `admin_ui_normalizers`. A `conftest.py` or test module
    overrides it with `Widgets([...])` of instances; the built-ins are added behind them by
    `Widgets` itself, so an override never restates them. Per-test tables are out of scope.

11. **Plumbing beside `normalizers`.** `widgets` travels the same constructors `normalizers`
    does, as one more argument, and stops at `FormField`. One object holding both would rename
    the existing argument on every constructor for no gain, since only `FormField` reads the
    widget classes.

12. **The test project's widget.** `Feed` gains `colour`, a `CharField(max_length=10, blank=True,
    default="")` holding `"red"`, `"green"` or `"blue"`. `FeedAdmin` draws it with
    `SwatchPicker`, a Django widget of the project's own in `shop/widgets.py`: a hidden input
    named `colour` and three buttons, which a short inline script turns into the hidden input's
    value and marks with `aria-pressed`. It fits use case 1, and without a widget class it is a
    real failure: `value` reads the hidden input through `TextWidget`, `fill` fails on it. Its
    widget class, `SwatchPickerWidget`, lives in `shop/kit_widgets.py`, a module of its own so the
    Django widget and the package's class are not confused. A model field rather than a form-only
    one, so a save is checked in the database. Its widget class drives the swatches through
    `field.native`, so the C4 tests also demonstrate criterion 35, driving a project-specific
    widget through a field's native handle, and it is marked done with criterion 34.

## Validation rules for the new setting

`DJANGO_ADMIN_KIT["widgets"]`:

* **Required:** no; it defaults to `[]`, meaning the built-in widget classes only.
* **Type:** a list or a tuple of strings. Anything else: `"DJANGO_ADMIN_KIT['widgets'] must be a
  list of dotted paths to widget classes, not dict."`
* **Size:** any length, `[]` included. Order is meaningful (decision 6).
* **Each element:** a string, a dotted path. Not a string: `"DJANGO_ADMIN_KIT['widgets'][0] must
  be a dotted path to a widget class, not type."` Repeating a path is allowed: the first one wins
  and the repeat never gets a field, so it is harmless.
* **Import:** a path that does not import: `"DJANGO_ADMIN_KIT['widgets'][0] names '...', which
  cannot be imported: {error}"`.
* **Class:** the path must name a class: `"... names '...', which is not a class."`
* **Shape**, checked on the instance:
  * `selector`, `read` and `fill`: required, callable. `"... names '...', which has no read
    method."`
  * `choices`: optional; when present, callable.
* **What `selector` returns** can only be checked when it runs: a non-empty string, or
  `TypeError: "SwatchPickerWidget.selector() must return a non-empty CSS selector, not None."`
  Whether it is valid CSS is only known to the browser: `querySelector` rejects it with a
  `SyntaxError` quoting the selector, on first use.

Errors are `ImproperlyConfigured`, raised once with the rest of the settings (28.4), naming the
position in the list as the rules name their kind.

## Commit plan

### C0: spec and plan

* `specification.md`
  * 28.5 rewritten along decisions 1 to 10, with the setting example, the interface and the
    built-in widget classes;
  * 28.1 lists `widgets` beside the other settings;
  * 27 lists five fixtures, `admin_ui_widgets` with them;
  * 1.3.0: radio buttons, split date-times and the rest each arrive as a built-in widget class,
    and a project can write its own meanwhile.
* this plan.

Consistent: documents only.

### C1: the package's controls as widget classes

* `widgets.py` (new): `CheckboxWidget`, `SelectWidget` and `TextWidget` with `selector`, `read`,
  `fill`, and `choices` on `SelectWidget`; `_option` and `_option_spellings` move here from
  `fields.py`; `Widgets()` holding the three and `widget_for(field)`: the first whose selector
  matches, found in one browser call (decision 2), else `TextWidget`, which keeps today's
  behaviour for a control nobody recognises.
* `fields.py`: `value`, `fill` and `choices` ask a module-level `Widgets()` for the field's
  widget class. The three branches go.
* Tests: none new. The field, choice and populate tests (`tests/test_fields.py`,
  `tests/test_choices.py`, `tests/test_populate.py`) are the proof that nothing changed, and they
  pass unchanged.

Consistent: a pure move; every field reads and fills as before.

### C2: report a field no widget class recognises

* `widgets.py`: `widget_for` returns `None` when no selector matches.
* `fields.py`: `value` and `fill` raise `LookupError` at once for `None`:
  `"The field 'refreshed_at' has no widget the package can read. A project teaches it one
  through DJANGO_ADMIN_KIT['widgets']."` (and "fill" for `fill`); `choices` answers `[]`.
* Tests (`tests/test_fields.py`, `tests/test_populate.py`): `refreshed_at` read and filled,
  exact messages; `populate(feed)` reports the same rather than timing out. The feed's fields
  tests do not otherwise change.

Consistent: only fields that used to time out behave differently. The message names a setting
that C3 adds; the two land on the same branch before any release.

### C3: read a field through a project's widget class

* `config.py`: `widgets` in `_KNOWN_KEYS`; `Config.widgets: tuple[Any, ...] = ()`; `_widgets()`
  importing, instantiating and checking `selector` and `read` (validation rules above, minus
  `fill` and `choices`).
* `widgets.py`: `Widgets(project=())` puts the project's classes in front of the built-ins;
  `widget_for` checks what `selector` returns.
* `plugin.py`: session fixture `admin_ui_widgets(admin_ui_config)`; `admin_ui` takes it and passes
  it to `AdminSession`.
* `session.py`, `pages.py`: `widgets` beside `normalizers` through `AdminSession`, `AdminPage`,
  `ModelPage`, `_page_at` and the three places that call it, and into `FormField` from
  `FormPage.fields`, which replaces C1's module-level table.
* Test project: `Feed.colour` and migration `0004_feed_colour.py`; `shop/widgets.py` with the
  `SwatchPicker` Django widget and its template under `shop/templates/shop/widgets/`; `FeedAdmin`
  draws `colour` with it; `shop/kit_widgets.py` with `SwatchPickerWidget`.
* Tests:
  * `tests/test_widgets.py` (new), overriding `admin_ui_widgets` at the top of the module:
    * a field whose box holds the widget class's control reads through it;
    * a field without it reads through the built-ins as before (`source`);
    * the first of two matching widget classes wins;
    * a project's subclass of `SelectWidget` that reads the bare value replaces the built-in on
      `category`;
    * a selector that returns `None` is reported, exact message;
    * a rendered-only field is read by its rule, not a widget class (a viewer on the feed).
  * `tests/test_config.py`: `widgets` accepted and instantiated in order; each rejection above.
  * `tests/test_plugin.py`: the fixture is listed.
  * `tests/test_pages.py`, `tests/test_changelist_count.py`: the fake-page builders pass
    `admin_ui_widgets`.
  * Any test listing the feed form's fields gains `colour`.

Consistent: with no `widgets` setting the table is the built-ins, as in C2; the swatch is read by
its widget class only where the test module installs it.

### C4: fill a field through a project's widget class

* `config.py`: `fill` required and callable.
* `fields.py`: nothing; `fill` already goes through the table since C1.
* Tests in `tests/test_widgets.py`:
  * `fill` clicks the swatch through `field.native`, and `value` reads it back;
  * `populate` from a dictionary and from a namespace fills `colour` with the rest;
  * a widget of several inputs: with the test-local `SplitDateTimeWidget` of decision 4 next to
    the swatch one, `fill` spreads a `datetime` over `refreshed_at_0` and `refreshed_at_1`, `value`
    reads the pair back, and `populate(feed)` fills the feed's form from the instance;
  * a save stores the colour;
  * an invalid save (blank `source`) renders the colour back;
  * `test_config.py`: a widget class without `fill`.

Consistent: C3 accepted a widget class without `fill`; from here it is rejected, and every class
in the suite has one.

### C5: a widget class's choices

* `config.py`: `choices`, when present, must be callable.
* `fields.py`: `choices` returns `[]` for a widget class without the method.
* Tests: the swatch offers its three choices in order; a widget class without `choices` offers
  `[]`; `test_config.py`: a `choices` that is not callable.

Consistent: the built-ins keep their choices; only project classes are affected.

### C6: README and spec

* `README.md`: an entry "Teaching the package a widget" with the swatch class, the setting, the
  fixture override, replacing a built-in by subclassing one, and the warnings of decision 5;
  `widgets` in the settings example; five fixtures.
* `specification.md`: 28.5 and 28.1's "field handling" marked done, criterion 34 fully done,
  and criterion 35 done.
* Remove this plan.

Consistent: documents only.
