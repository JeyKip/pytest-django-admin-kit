# Normalization rules: implementation plan

Spec section 28.3, the "value normalization" item of 28.1, the part of acceptance criterion 34
(section 32) about normalization, and the references to 28.3 in sections 3.4 and 9.8.
Field handling hooks (28.5) are a separate change.

## Scope

* Every rule that turns a rendered value into the value a test reads is replaceable for the whole
  project, in `DJANGO_ADMIN_KIT["normalizers"]`.
* The package decides which rule reads a value from what stands behind it: the model field of a
  changelist column or a rendered-only form field, then what the admin drew. A rule handles one
  kind of value and never has to tell kinds apart.
* The default set of section 28.3, with dates and times split by kind: `boolean`, `empty`,
  `link`, `date`, `datetime`, `time`, `number`, `choice`, `text`.
* README and spec updates.

Out of scope:

* the value of an editable form field, which is what its control holds (a checkbox's state, the
  chosen option, the typed text) and goes through no rule;
* rules chosen per column or per field name, which the spec lists under "Later";
* replacing a rule for a single test, and adding a kind for a representation the package does
  not know, such as a model field class of the project's own; the spec lists both under
  "Later";
* field handling hooks (28.5).

## How a value is read today

* `RenderedValue.value` (`src/django_admin_kit/rendered.py`) calls `normalize.normalize`, which
  tries the module-level `RULES` (`boolean`, then `text`) in order; the first that does not
  return `NOT_HANDLED` wins.
* Two classes read through it: `Cell` (`rows.py`), a changelist cell, and the rendered-only
  `FormField` (`fields.py`, via `FormField._rendered`).
* `Cell` knows its column's configured name; `FormField` knows its field name; the pages know
  the model (`ModelPage._model`).
* `AdminSession` (`session.py`) builds every page, and pages build the next page in
  `AdminPage._submitted` → `_page_at` and in `EditPage.delete`.

## What decides a value's kind

The admin renders a value from the model field behind it, and the package can find that field:

* a changelist column is named as `list_display` names it (`column-<name>`). Django resolves a
  name to a model field first, then to a callable or a method (`admin.utils.lookup_field`), so
  `django.contrib.admin.utils.get_fields_from_path(model, name)` finds the field, including a
  `category__name` path (Django 5.1+), and raises for a method or a callable;
* a rendered-only form field has the field's name, resolved the same way.

A value with no model field behind it, such as the method `price_with_tax`, is still read by a
rule, picked by what the admin drew: `empty`, a lone boolean icon, links, or else `text`. It is
never given a field's kind: the admin renders a method's result as text, and `@admin.display`
says nothing of its type, so `price_with_tax` reaches `text`, never `number`. A project that
wants it typed parses it in its `text` rule. Choosing a rule by column is left for later
(section 33, "Later").

## Decisions and assumptions

1. **A rule is a callable taking the rendered value and returning the value a test reads.** It
   gets the same `RenderedValue` it does today, with one addition, `field`: the model field
   behind the value, or `None`. A rule always answers; `NOT_HANDLED` goes, since the package
   picks the rule rather than asking each in turn.
2. **The kind is picked in this order, first match wins:**
   1. `empty`: the text is what the admin shows for a value it has none of in that column
      (decision 4);
   2. `choice`: the field has choices, which the admin renders as their labels whatever the
      field's class;
   3. the kind for the field's class, the most specific class first along its MRO: `boolean`
      for `BooleanField`, `date` for `DateField`, `datetime` for `DateTimeField` (a subclass of
      `DateField`, so the more specific kind wins), `time` for `TimeField`, `number` for
      `IntegerField`, `DecimalField` and `FloatField`;
   4. with no kind from the field: `boolean` when the admin drew a lone boolean icon (a method
      column with `boolean=True`), else `link` when the value renders links;
   5. `text`.
   A linked date column is therefore read by `date`, and its links stay in `links`.
   Dates, date-times and times are separate kinds because a project that types them parses
   each differently and wants a `date`, a `datetime` or a `time` back; one rule for all three
   would have to look at `field` to tell them apart, which is what the kinds are for.
3. **The defaults read what the user reads**, so nothing changes until a project replaces a
   rule: `boolean` reads the icon's `alt` as `True`, `False` or `None`; every other default
   returns the text. Each is a documented function in `normalize.py`.
4. **`empty` compares the text with the empty value display the admin used for that value**,
   resolved from the same sources, in the same order, as the admin itself:
   * on a changelist, the display function's own `empty_value` when the column is a method or
     a callable that sets one (`@admin.display(empty_value=...)`), else the model admin's
     `empty_value_display`, else the site's;
   * on a form, the model admin's, else the site's: the admin ignores a display function's own
     value for a rendered-only field, so the package does too.
   The model admin's `get_empty_value_display()` already falls back to the site's. An empty
   string is drawn as nothing, never as the empty display, so it reads as `text`. The admin
   marks an empty value in no other way, so a value whose text is the display itself (a name
   that is literally `"-"`) reads as empty.
5. **One place reads the site's registry.** The model admin comes from
   `AdminSite.get_model_admin` on Django 5.0+, and from the site's registry before, which has
   no public accessor. `urls.py` already reads the registry to list the registered models in
   an error. Both go through two helpers in `urls.py`, `registered_models(site)` and
   `model_admin(site, model)`, built on one private accessor, so the registry is read in one
   place and `urls.py`'s error uses the first.
6. **Settings hold dotted paths, as `site` does:** `"normalizers": {"date":
   "shop.rules.as_date"}`. A settings module that imported the rule would import project code
   before the app registry is ready. Paths are imported and checked when the configuration is
   built, once per session, before the first page opens.
7. **The settings are validated loudly**, like every other setting: a name that is not one of
   the kinds is rejected, naming it and listing the kinds; a value that is not a string, a path
   that does not import, and one that names no callable are each rejected, naming the kind.
8. **The rules are built once per session**, from the configuration, by a session-scoped
   fixture, `admin_ui_normalizers`, the way `admin_ui_urls` is built. A project may override it
   for a directory or a module of tests without restating the rest of the settings; a
   function-scoped override fails, so it cannot replace rules for a single test. `admin_ui`
   hands the table to the session, which hands it to every page and everything taken from it,
   next to the `check` each already gets. Nothing changes them during a test.

### `Feed.refreshed_at` and `Feed.refresh_time` (test project only, C2)

| Field | Rules |
| --- | --- |
| `refreshed_at` | `DateTimeField(null=True, blank=True)`; optional; when the feed was last refreshed |
| `refresh_time` | `TimeField(null=True, blank=True)`; optional; the time of day it refreshes |

* Editable on the feed's form, which shows every field; existing feeds and fixtures leave both
  empty, and the form accepts them empty. Tests that need a value set it on the instance.

## Commit plan

### C0. Spec and plan

* `specification.md` §28.3:
  * the rule signature (decision 1), the order kinds are picked in (decision 2), the defaults
    (decision 3), `empty` (decision 4);
  * the settings in dotted paths (decision 6) and their validation (decision 7);
  * what is out of scope: editable fields, per-column rules.
* Already in the working tree: dates, date-times and times as three kinds; dotted paths in the
  example; per-test replacement and new kinds moved to section 33 "Later", and dropped from
  §3.9 and from §32 item 34.
* This plan.

### C1. Replace a rule for the whole project

The table, its plumbing and its settings, with the two rules there are today.

* `normalize.py`: `Normalizers`, the table of kind name to rule, built from the defaults and the
  project's replacements, with `read(rendered)` doing what `normalize()` does now. `RULES` and
  `normalize()` go.
* `config.py`: `normalizers` among the known keys; `Config.normalizers`, the kind names mapped to
  the rules, imported with `django.utils.module_loading.import_string` and validated as
  decision 7 says.
* `plugin.py`: `admin_ui_normalizers`, a session-scoped fixture that builds the table from
  `admin_ui_config`; `admin_ui` hands it to the session.
* `specification.md` §27: `admin_ui_normalizers` among the fixtures `admin_ui` is assembled
  from.
* `pages.py`, `rows.py`, `fields.py`, `rendered.py`: the table is passed down from the session to
  each page, to the pages a page leads to (`_submitted`, `_page_at`, `EditPage.delete`), and to
  every `Row`, `Cell`, `FormField` and `RenderedValue`.
* `tests/project/shop/rules.py`: rules that tag what they receive, such as `("text", text)`, so a
  test sees which rule read each value.
* Tests:
  * `tests/test_config.py`: a path is imported; a name that is no kind, a value that is not a
    string, a path that does not import, and one that names no callable are each rejected with
    the exact message;
  * a new `tests/test_normalizers.py`, which overrides `admin_ui_normalizers` for the module
    with the tagging rules, as a project overrides it (section 27): text cells read through `text`, icon
    cells through `boolean`, a rendered-only form field through its rule, and the page a
    submission leads to reads through the same rules.
* `tests/test_plugin.py`: `admin_ui_normalizers` among the fixtures the plugin registers.
* Constructors that tests call directly (`tests/test_pages.py`'s `page_at`) gain the argument.
* Consistency: without `normalizers` the defaults read as today, so every other test passes
  unchanged.

### C2. Pick the rule by the model field behind a value

* `RenderedValue` takes the page's model and the name the value is rendered under (a `Cell`'s
  column, a rendered-only `FormField`'s name), and `RenderedValue.field` resolves the model
  field from them with `get_fields_from_path` when it is read; `None` when the name is no
  field. C3 needs the model and the name again, for the empty display.
* `normalize.py`: the kinds `choice`, `date`, `datetime`, `time` and `number`, each returning the
  text; the table maps field classes to kinds, most specific first; `read` picks the kind in the order of
  decision 2, steps 2, 3, 4 (boolean only) and 5. `boolean` is also picked by `BooleanField`.
* `tests/project/shop/models.py`: `Feed.refreshed_at` (`DateTimeField`) and `Feed.refresh_time`
  (`TimeField`), both optional, and a migration `0003_feed_refresh.py`, so a changelist shows a
  date-time and a time. No test reads the feed's form fields or columns by name.
* `tests/project/shop/admin.py`: `FeedAdmin.list_display = ("source", "mode", "refreshed_at",
  "refresh_time", "refreshed")`, so a changelist shows a field with choices, a date-time, a time
  and a method drawn as a boolean icon.
* `tests/project/shop/rules.py`: a tagging rule for each new kind.
* Tests in `tests/test_normalizers.py`, through the tagging rules:
  * `date` receives the release date cells, and no other column;
  * `datetime` receives the feed's `refreshed_at` cells and not the release dates, although
    `DateTimeField` is a `DateField`;
  * `time` receives the feed's `refresh_time` cells;
  * `number` receives the price cells;
  * `choice` receives the feed's mode cells, read by their label;
  * `boolean` receives `is_active` and `featured` by their field, and the feed's `refreshed`, a
    method with `boolean=True`, by its icon (`is_released` sets no `boolean`, so the admin
    renders it as text and `text` reads it);
  * a rendered-only form field is read by its field's kind (a viewer's product page: the date by
    `date`, the quantity by `number`);
  * the value a rule receives has `field`, the model field, and `None` for a method column.
* Consistency: every new default returns the text, so values read as before.

### C3. Links and empty values

* `normalize.py`: `link` (step 4) and `empty` (step 1), both returning the text.
* `rendered.py`, `rows.py`, `fields.py`, `pages.py`: the pages hand the model admin down in
  place of the model (the model is `model_admin.model`), and `RenderedValue.empty_display`
  resolves the display as decision 4 says: the model admin's, and for a `Cell` first the
  column's own display function, looked up as the admin looks it up (a callable in
  `list_display`, then the model admin's attribute, then the model's). The spec's rule
  description gains `empty_display`.
* `urls.py`: `registered_models(site)` and `model_admin(site, model)` on one private accessor
  of the site's registry (decision 5); `AdminUrls._reverse_model`'s error lists the models
  through `registered_models`, so it reads the registry no longer on its own.
* `tests/project/shop/rules.py`: tagging rules for `link` and `empty`.
* Tests in `tests/test_normalizers.py`:
  * `link` receives the documents column, a method that renders two links, and the linked
    `name` column, a `CharField`, which has no kind of its own; it does not receive the SKU,
    which is not linked;
  * `empty` receives a missing release date, `"(none)"` under the product admin's own display,
    and not the dates that are set;
  * `empty` receives `price_with_tax` on the add page, a method that returns the empty display;
  * a method column that sets its own `empty_value` is read as empty by it, not by the model
    admin's display: `FeedAdmin.last_refreshed`, added to the feed's columns with
    `@admin.display(empty_value="never")`, reads `"never"` through `empty` for a feed never
    refreshed, while `refreshed_at` reads the site's default `"-"`. No test reads the feed's
    columns by name, so the column changes nothing else;
  * a rendered-only form field with no value reads the model admin's display through `empty`;
  * the linked `name` column, read by `text` in C1 and C2, is now read by `link`, so those tests
    read the SKU instead.
* Consistency: both defaults return the text.

### C4. README, spec marks and plan removal

* `README.md`: an entry for replacing a rule for the whole project, with the kinds and the
  order they are picked in; `admin_ui_normalizers` in the list of fixtures a project may
  override.
* `specification.md`: `(done)` on §28.3, the "value normalization" item of §28.1, the
  normalization half of §32 item 34 (the field-handling half waits for 28.5), and the references
  in §3.4.
* Delete this plan.
