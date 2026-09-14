# Changelist rows: reading cells, normalizing values, matching rows

Implements specification §9 (Changelist Row Matching) in full, and the parts of other
sections without which §9 cannot be marked done:

* §3.4 normalized values for changelist cells: booleans, empty values, links, numbers, dates
  and times, text;
* §3.5 addressing of rows and cells, and §3.6 native handles on `Row` and `Cell`;
* §6.3, the paragraph on link targets comparing equal to the package's URLs;
* §8.2, the `page.rows == []` line;
* §30, the failure output of a row match;
* §32 criteria 9 and 10.

## 1. Scope

Built:

* `page.rows`: a list of `Row`, in the order shown; `[]` on an empty changelist; raises on a
  changelist that did not open, like every other reader.
* `Row`: `row["email"]` and `row[2]` give a `Cell`; `row.index`, `row.native`, `row.object`.
* `Cell`: `value` (typed, per §3.4), `text` (what the document shows, before
  normalization), `is_empty` (the `empty` rule's answer), `links` (list of `Link` objects
  with `.text`, `.target` as a path and `.href` exactly as rendered, each comparing equal to
  a `(text, target)` pair), `native`.
* Normalization of a cell's value: boolean icon to `True`/`False`/`None`; the empty value
  the admin renders, at whichever of its three levels it was set, to `""`; integer, decimal and float fields to `int`, `Decimal`, `float`; date, time
  and datetime fields to `date`, `time` and an aware `datetime` in the project's time zone,
  parsed through the project's own format settings; everything else to text. Link targets
  normalized to paths.
* `page.contains(pattern)` and `page.contains([patterns])`; `page.match(pattern)` and
  `page.match([patterns])`; the sentinels `ANY` and `ANY_ROW`; callables `matcher(row, cell)`;
  tuple, list and dictionary patterns.
* A failing `assert page.contains(...)` prints the expected pattern and the actual rows, as
  §30 shows, through pytest's ordinary assertion output.
* `page.count` reads its number through the number normalizer, closing the stopgap noted in
  `_count_line`.
* Spec marks, README, tests, and additions to the test project's `Product` and its admin.

Out of scope:

* The settings surface of §28.3 (`DJANGO_ADMIN_KIT["normalizers"]`, `admin_ui.normalizer(...)`).
  The rules are built as one replaceable table so that §28.3 only has to read settings into
  it; see decision 3.
* `list_editable` cells, and every other changelist interaction of §33 (1.2.0).
* Form fields (§10 onwards). `links` on a rendered-only field (§13.4) reuses `Cell`'s
  pair type when it is built.

## 2. Where the change goes

| Layer | File | What exists | What this adds |
|---|---|---|---|
| Session | `src/django_admin_kit/session.py` | `list(model)` via `_open()` | passes the model to the page |
| Page | `src/django_admin_kit/pages.py` | `ChangelistPage` with `count`, `headers`, `columns`, `_header_cells`, `_shown()`, `_text()`, `_token()` | `rows`, `contains`, `match`; the model behind the page |
| Rows | `src/django_admin_kit/rows.py` (new) | | `Row`, `Cell`, `Link` |
| Normalization | `src/django_admin_kit/normalize.py` (new) | | the rule table and each rule |
| Date parsing | `src/django_admin_kit/dateformats.py` (new) | | the inverse of Django's date format language |
| Matching | `src/django_admin_kit/matching.py` (new) | | `ANY`, `ANY_ROW`, pattern matching, the result object |
| Test project | `tests/project/shop/models.py`, `admin.py` | `Product` with name, sku, price, is_active, released_on; `ProductAdmin` with `price_with_tax` | a `DateTimeField` and a `TimeField`, a nullable boolean, an integer and a float field, a `DateTimeField` the admin renders as "2 hours ago", a two-link column, an `empty_value_display` on the admin and on a column; a `Category` model whose admin has no change links |

Reused as is: `_shown()` for the guard, `_text()` for text, `_token()` for the `field-<name>`
class, `page.columns` for the column order, `AdminUrls` and the `destination` path rule for
link targets, `apps.get_model` style public lookups (`model._meta.get_field`), and the
`conftest.py` users and products.

## 3. Markup and rendering facts the code depends on

Checked in Django 3.2, 4.2, 5.2, 6.0 and 6.1, and by rendering the test project's changelist
on 3.2, 5.2 and 6.1:

1. Rows are `#result_list tbody tr`. Each cell is a `th` or `td` with class `field-<name>`,
   where `<name>` is the same token as the header's `column-<name>`, so cells and columns
   line up by position once `td.action-checkbox` is skipped (as `_header_cells` already
   skips `th.action-checkbox-column`). A `list_editable` form adds a row with a `colspan`
   before a row with errors; out of scope, and it has no `field-` cells so it is not a row.
2. The first `list_display_links` column is a `th` holding `<a href=".../<pk>/change/">`.
   With preserved filters the href carries `?_changelist_filters=...`. `list_display_links =
   None` renders no link at all.
3. `display_for_field` (`django/contrib/admin/utils.py`, unchanged in shape across the
   matrix) renders, in this order: a field with choices as its label; a `BooleanField` as
   `<img alt="True|False|None">` (`icon-yes`, `icon-no`, `icon-unknown`); `None` as the
   empty value display; `DateTimeField` as `localize(template_localtime(value))`, i.e. the
   project's `TIME_ZONE` and `DATETIME_FORMAT`; `DateField`/`TimeField` through `DATE_FORMAT`
   and `TIME_FORMAT`; `DecimalField` through `number_format(value, decimal_places)`;
   `IntegerField`/`FloatField` through `number_format`; `FileField` as a link; anything else
   through `display_for_value`, which renders a `bool` returned by a method column as text
   unless the method sets `boolean = True`, in which case as the icon.
4. Formats come from `django.utils.formats.get_format`, which respects `USE_L10N` (default
   `False` up to 4.x, always on from 5.0) and the active language. Under `en`: `DATE_FORMAT
   = "N j, Y"` ("Jan. 1, 2026", AP month names), `DATETIME_FORMAT = "N j, Y, P"` ("Jan. 1,
   2026, 3:30 p.m.", no seconds), `TIME_FORMAT = "P"`, decimal separator `.`, thousand
   separator `,` applied only under `USE_THOUSAND_SEPARATOR`. Other locales use other format
   strings (`j F Y`, `d.m.Y H:i`) and separators (`,` and a non-breaking space).
5. The month and day names those formats produce come from `django.utils.dates` (`MONTHS`,
   `MONTHS_3`, `MONTHS_AP`, `MONTHS_ALT`, `WEEKDAYS`, `WEEKDAYS_ABBR`), translated for the
   active language. `P` renders "midnight", "noon", "3 p.m." or "3:30 p.m."; `f` renders
   "3" or "3:30"; `S` renders an English ordinal suffix.
6. The empty value is `AdminSite.empty_value_display`, default `"-"`, on every version. A
   `ModelAdmin` may override it, and a method column may set its own; reading the
   `ModelAdmin` needs `AdminSite.get_model_admin`, which exists only from Django 5.1, or the
   private `_registry`.
7. The same live server thread and the test process share settings, so the format the page
   was rendered with is the format `get_format` returns in the test, as long as the language
   is the same: the browser locale is pinned to `LANGUAGE_CODE` (§28.4), and the test process
   runs with `LANGUAGE_CODE` active.

## 4. Decisions

1. **A cell is read from the page and typed by the model field behind its column.** The
   column name is the `list_display` entry; `model._meta.get_field(name)` finds a field for
   it or raises `FieldDoesNotExist`, in which case the cell is a computed column and only
   markup-based rules apply (boolean icon, empty value, links, text). This needs no
   `ModelAdmin` and no private attribute.
2. **`value` is the meaning, at the precision the page shows.** A `DateTimeField` rendered
   without seconds gives a datetime with `second=0`; the package does not go to the database
   to recover what the page did not show. Tests compare against values the page can show.
3. **Rules are a table, tried in order, first answer wins.** `boolean`, `empty`, `link` (for
   `links`, not `value`), `number`, `datetime`, `text`. Each rule is a function
   `(cell, column) -> value` returning a private `NOT_HANDLED` marker to pass. The table is a
   module-level dict keyed by the names §28.3 lists, so that section can replace entries from
   settings without restructuring. Until then the table is not public.
4. **Dates are parsed by inverting Django's own format language**, not with `strptime`.
   `strptime` has no `N` (AP month names), no `P`, and its month names come from the C
   locale, not Django's translations. A small parser turns a format string into a regular
   expression using the translated names of fact 5. It accepts the whole language, since a
   project may put any of its characters into its own `DATE_FORMAT`: the characters that
   carry a part of the value (`d j m n F M N b E y Y H G h g i s u A a P f`, the offset `O`
   and `Z`, the epoch `U`) are parsed and used; those redundant once a date is known (`D l S
   w z W o t L I e T`) are matched so the text lines up and then ignored; the composites `c`
   and `r` expand to their fixed sub-formats. Escaped literals pass through.
5. **A typed cell whose text does not fit is left as text, with a warning.** `list_display`
   resolves a name on the `ModelAdmin` before the model, so an admin method named after a
   field renders that column itself while the field lookup still finds a `DateField` or a
   `DecimalField`. Raising there would make the whole row unreadable and break a `contains`
   on unrelated columns. Instead the `number` and `datetime` rules emit
   `NormalizationWarning` (a `UserWarning` subclass in `normalize.py`, naming the column,
   the text and the format) once per column per page, and `value` is the text; a test that
   compares it to a date then fails on its own terms, and `text` and `is_empty` keep
   working. A project that wants the strict behaviour turns the warning into an error with
   `-W error::django_admin_kit.normalize.NormalizationWarning`. `value` is computed lazily
   per cell and cached, so a column nobody reads never warns.
6. **Numbers are parsed with the project's separators.** The thousand separator is removed
   only when `USE_THOUSAND_SEPARATOR` is on, the decimal separator becomes `.`, and the field
   type decides `int`, `Decimal` or `float`. `page.count` uses the same rule.
7. **The empty value is resolved at all three levels Django resolves it**: the column's
   own (`@admin.display(empty_value=...)`, an attribute on the method), else the
   `ModelAdmin`'s (`get_empty_value_display()`), else the site's. That is what
   `items_for_result` does when rendering, so the rule recognises exactly what the page
   shows. Reaching the `ModelAdmin` uses `AdminSite.get_model_admin(model)` from Django
   5.1 and `site._registry[model]` before that, in one private helper with a comment saying
   why the registry is touched: no public route exists on those versions, and the
   registry's shape has not changed since Django 1.x.
8. **A link keeps both forms of its target.** `Link.target` is the path, through the same
   rule as `destination` (`urlsplit(...).path`), so `?_changelist_filters=...` and an
   absolute form both compare equal to `admin_ui.url.edit(obj)`; that is the §6.3
   paragraph. `Link.href` is the attribute exactly as rendered, for a test about how the
   admin built the link, such as preserved filters. `Link` is a small class, not a tuple,
   and compares equal to a `(text, target)` pair so the spec's `links == [("Bolt", url)]`
   holds; it is the one place the package implements comparison behaviour, per §3.1,
   because a third field would otherwise make every pair comparison carry a query string.
9. **`row.object` comes from the change link.** `resolve(target)` on the first link whose
   path resolves to the model's change view gives `object_id`; the instance is fetched with
   `model._default_manager.get(pk=...)`. A row without such a link has `object` `None`.
10. **`contains` and `match` return a result object, not a bare bool.** It is falsy when the
   match failed and its `repr` is the §30 text (expected pattern, actual rows, and for
   `match` which position failed). `assert page.contains(...)` then prints that text through
   pytest's ordinary assertion rewriting, with no hook. A truthy result reprs as `True`-like
   text so a passing assertion reads normally.
11. **A collection matches distinct rows, in any order, by backtracking.** Each pattern must
    take a different row; greedy assignment would fail `[ANY_ROW, ("Jane", ...)]` against
    `[Jane, John]`. Changelists are at most one page, so the search is cheap.
12. **A list is a collection when every element is a row pattern** (tuple, list, dict,
    `ANY_ROW`); otherwise it is one row. `[]` is an empty collection: `contains([])` is true,
    `match([])` means no rows.
13. **The sentinels are plain objects with a `repr`.** With `.values` gone from the spec they
    never meet `==`, so no `__eq__`.
14. **The test project gains what the rules need**: `Product.created_at` (`DateTimeField`),
    `Product.featured` (`BooleanField(null=True)`) for the unknown icon, `Product.quantity`
    (`PositiveIntegerField(default=0)`, the field §13.2 already imagines) and
    `Product.weight` (`FloatField(null=True, blank=True)`) so every numeric type reaches a
    real page, `Product.last_bought_at` (`DateTimeField(null=True, blank=True)`) rendered
    by a `ProductAdmin` method of the same name as "2 hours ago" through
    `django.utils.timesince`, so a typed column carries text the format cannot explain,
    `Product.restock_at` (`TimeField(null=True, blank=True)`, the time of day the shelf is
    restocked) so a time reaches a page next to the date `released_on` already gives, a
    `documents`
    method column rendering two links, and a second model, `Category(name)`, registered on
    the default site with `list_display_links = None`, for a row that links to nothing. The
    spec's own examples already name `Category` next to `Product`. The migration is
    regenerated with the command in the README. Existing header and column assertions in
    `tests/test_changelist.py` are extended with the new columns, and `tests/test_index.py`
    gains `Category` in the default site's lists.
15. **Branch:** `feature/changelist-rows`, already holding the spec changes. This plan file
    is committed on the branch while it is being refined and removed once every slice is in.

## 5. Field validation rules

Not applicable to the package: no settings, serializers or writable fields are added. The test
project's new model fields are fixtures for the suite (`created_at` with an explicit value in
every test that reads it, `featured` nullable, default `None`).

## 6. Commit plan

### R1. Read the rows and cells of a changelist as text

`src/django_admin_kit/rows.py` (new): `Cell` (`text` as the document's whitespace-collapsed
text, `value` equal to it for now, `native`, `_name`, `_field`), `Row` (`__getitem__` by name or position, `index`, `native`, `_cells` built from
`tr > th, tr > td` minus `.action-checkbox` and `page.columns`). A missing name raises
`KeyError` naming it and listing the row's columns, as `models_for` does.

`src/django_admin_kit/pages.py`: `ChangelistPage.rows` (cached, through `_shown()`, `[]`
when there is no table); the page keeps the model it was opened for.

`src/django_admin_kit/session.py`: `list()` hands the model to the page.

`tests/test_rows.py` (new): a viewer reads `page.rows[0]["name"].value == "Bolt"` and
`.text == "Bolt"`, by position, `row.index`, `len(page.rows) == 3` in the admin's order; an unknown column raises;
an empty changelist has `rows == []`; a refused page raises on `rows`; `row.native` and
`cell.native` are Playwright locators (`cell.native.text_content()`).

`tests/test_changelist.py`: the "did not open" test gains `rows`.

Spec: §8.2 `page.rows == []` `# done`; §3.5 examples `# done` for rows and cells; §3.6
`page.rows[0].native` and `page.rows[0]["email"].native` `# done`.

Consistency: `rows` is new; nothing reads it yet.

Commit: `Read the rows and cells of a changelist by column name and position`.

### R2. Normalize boolean icons and the empty value

`src/django_admin_kit/normalize.py` (new): the rule table with `boolean` (icon `alt` to
`True`/`False`/`None`), `empty` (text equal to the empty value the admin renders for that
column, resolved per decision 7, to `""`) and `text`; `Cell.value` runs the table;
`Cell.is_empty` asks the `empty` rule alone; the `_model_admin(site, model)` helper of
decision 7.

Test project: `Product.featured = BooleanField(null=True)` in `list_display`; migration.
`ProductAdmin.empty_value_display = "(none)"`, and a method column
`@admin.display(description="Release", empty_value="unreleased") def release(self, product):
return product.released_on`, so the suite has the `ModelAdmin` level and the column level on
one page; `ops_site` keeps the site default `"-"`.

`tests/test_rows.py`: `is_active` reads `True`/`False`; `featured` reads `None` when unset;
`released_on` unset has `is_empty`, `value == ""` and `text == "(none)"`; `release` unset
likewise with `text == "unreleased"`; a boolean icon has `text == ""` and `is_empty` false; a method column returning a bool without
`boolean=True` reads `"True"` as text (what the user sees).
`tests/test_custom_site.py`: on `ops_site` an unset `released_on` reads `""` from the site's
`"-"`.
`tests/test_changelist.py`: headers and columns gain `"Release"` / `"release"`.

Spec: §3.4 first two bullets `(done)`; §9.8 boolean and empty examples `# done`; §9.3 `(done)`; §32 item 10's boolean
and empty parts noted in the plan, the item marked when links land.

Consistency: text cells are unchanged; only icon and empty cells change value. The
`ProductAdmin` override changes what the page shows for an empty date, and the only test
that could see it is the one written here.

Commit: `Normalize boolean icons and the empty value in changelist cells`.

### R3. Links on a cell, targets as paths, and the object behind a row

`src/django_admin_kit/rows.py`: `Link` (`text`, `target`, `href`; equal to a `(text,
target)` pair; repr shows all three) per decision 8; `Cell.links` from `a` elements;
`Row.object` per decision 9.

Test project: `ProductAdmin.documents` renders two links; `list_display` extended;
`Category` model and `CategoryAdmin(list_display=("name",), list_display_links=None)`;
migration. `tests/test_index.py`: the superuser's lists gain `Category` before `Product`.

`tests/test_rows.py`: the `name` cell's `links == [("Bolt", admin_ui.url.edit(bolt))]`; a
plain cell's `links == []`; `documents` gives two pairs and `.target` reads the second; with the list opened as
`?is_active__exact=1`, `links == [("Bolt", admin_ui.url.edit(bolt))]` still holds while
`links[0].href` carries `_changelist_filters`; `row.object == bolt`; `row.object is None` on the `Category` changelist, whose admin has
`list_display_links = None`, and its `name` cell has `links == []`.

Spec: §3.4 links bullet `(done)`; §6.3 link paragraph `(done)`; §9.8 links examples `# done`;
§32 item 10 `(done)`.

Consistency: additive.

Commit: `Expose a cell's links with normalized targets and the object behind a row`.

### R4. Typed numbers, and the count through the same rule

`src/django_admin_kit/normalize.py`: `number` rule for `IntegerField`, `DecimalField` and
`FloatField`, and through `isinstance` their subclasses (`AutoField`, `BigIntegerField`,
`PositiveIntegerField`, `SmallIntegerField`), using `get_format("DECIMAL_SEPARATOR")`,
`get_format("THOUSAND_SEPARATOR")` and `USE_THOUSAND_SEPARATOR`. `ChangelistPage.count`
parses through it; the stopgap comment goes.

Test project: `Product.quantity = PositiveIntegerField(default=0)` and `Product.weight =
FloatField(null=True, blank=True)`, both appended to `list_display` so no existing column
moves; migration. `tests/test_changelist.py`: headers gain `"Quantity"`, `"Weight"` and
columns `"quantity"`, `"weight"`.

`tests/test_normalize.py` (new, no browser): the exhaustive proof of the rule. Parametrized
over field type and rendered text: `IntegerField` and each subclass above to `int`,
`DecimalField` to `Decimal` keeping the field's `decimal_places` (`"10.00"` stays
`Decimal("10.00")`, not `Decimal("10")`), `FloatField` to `float`; grouping on and off
(`USE_THOUSAND_SEPARATOR`) under `en` (`1,234.5`), `de` (`1.234,5`) and `fr` (`1\xa0234,5`)
with `translation.override`; a negative number; a text the format cannot explain leaves
`value` as the text and emits one `NormalizationWarning` naming the column and the text
(`pytest.warns`), and a second cell of the same column on the same page adds no warning. Each case is built by rendering the value with
`django.utils.formats.number_format` first, so the text under test is what Django would
put on the page.

`tests/test_rows.py`: on a real page, `quantity` reads `int` (`3`, and `isinstance` checked),
`price` reads `Decimal("10.00")`, `weight` reads `float` (`0.5`) and `""` when unset; the
locale parametrization of R5 (`en-us`, `de`, `fr`, `ja`) covers these three columns as
well, with `USE_THOUSAND_SEPARATOR` on so the grouped form is seen in a browser too
(`quantity = 1234`).

Spec: §3.4 numbers half of the bullet; §9.8 example `"10.00"` becomes `Decimal("10.00")`.

Consistency: cells of numeric fields change type; nothing in the suite compared one yet.

Commit: `Normalize numeric cells through the project's number formats`.

### R5. Dates and times

`src/django_admin_kit/dateformats.py` (new): `parse(text, format) -> datetime` (with a
flag for what was present), the inverse of `django.utils.dateformat` per decision 4. The
month and weekday names it matches are the translated ones for the active language, so the
same parser serves every locale Django ships.

`tests/test_dateformats.py` (new, no browser): the parser is proved against Django itself,
character by character and locale by locale. One parametrized test formats a set of values
with `django.utils.dateformat.format` through a format string built around each character
of the language in turn (`"Y-m-d D"`, `"Y-m-d z"`, `"c"`, `"r"`, `"U"`, `"Y-m-d H:i O"`,
and so on) and parses the result back, so every character is met at least once. One parametrized test walks every `django/conf/locale/*/formats.py` that
defines `DATE_FORMAT`, `DATETIME_FORMAT` or `TIME_FORMAT` (about ninety languages), and
under `translation.override(language)` formats a set of values with
`django.utils.dateformat.format` and parses the result back, asserting equality. The
values cover day 1 and 31, every month (so every translated name is met, including the AP
and alternative sets), a year below 2000 for `y`, midnight, noon, 12:00 and 23:59, and a
time with and without minutes for `P` and `f`. Further: `parse` raises `ValueError` naming
the text and the format when they do not fit; the `datetime` rule turns that into the
warning and the text value of decision 5, tested in `tests/test_normalize.py`.
That is the full-matrix proof; the browser tests below then confirm the pipeline end to
end on a few representative locales.

`src/django_admin_kit/normalize.py`: `datetime` rule: `DateField` to `date`, `TimeField` to
`time`, `DateTimeField` to an aware datetime in `settings.TIME_ZONE`.

Test project: `Product.created_at = DateTimeField()`, `Product.last_bought_at =
DateTimeField(null=True, blank=True)` and `Product.restock_at = TimeField(null=True,
blank=True)` in `list_display`; migration. `ProductAdmin` gains
`def last_bought_at(self, product)` returning `f"{timesince(product.last_bought_at)} ago"`,
or `None` when unset, with a comment saying it shadows the field on purpose so the suite
has a typed column whose text is the admin's own. `tests/test_changelist.py`: headers gain
`"Created at"`, `"Last bought at"` and `"Restock at"`, columns `"created_at"`,
`"last_bought_at"` and `"restock_at"`.

`tests/test_rows.py`: `released_on` reads `date(2026, 1, 1)`; `restock_at` set to
`time(15, 30)` reads equal, set to midnight reads `time(0, 0)` (the `P` format's word
form), unset reads `""`; `last_bought_at` set two
hours before now reads `"2 hours ago"` as text with one `NormalizationWarning` naming the
column (`pytest.warns`), `is_empty` false, `text` the same string; unset it reads `""` with
`is_empty` true and no warning, since the empty rule answers first; `created_at` created as
`datetime(2026, 1, 1, 15, 30, tzinfo=utc)` reads equal (project zone is UTC); a second test
under `override_settings(TIME_ZONE="Europe/Kyiv")` still reads equal (aware comparison) and
`.hour == 17`. A test parametrized over `LANGUAGE_CODE` in `en-us`, `de`, `fr` and `ja`
(Latin and non-Latin formats, `N j, Y`, `j. F Y`, `j F Y`, `Y年n月j日`), with `USE_L10N`
set for the Django versions that still read it, opens the changelist in that language and
reads the same `date`, `time` and `datetime` back; the browser locale follows `LANGUAGE_CODE`
through the fixture, so nothing else changes. The number test of R4 is parametrized the
same way, so separators are proved in the browser too.

Spec: §3.4 dates/times bullet `(done)`; §31 "Values render through the formats and time zone
the project has configured" `(done)`.

Consistency: additive rule; date cells were text before.

Commit: `Normalize date and time cells by inverting the project's date formats`.

### R6. `contains` with one literal row, and the failure text

`src/django_admin_kit/matching.py` (new): `matches(pattern, row)` for a tuple or list of
literals, one per cell, compared with `==` against `cell.value`; a pattern of the wrong
length is no match. `MatchResult` per decision 10: falsy on failure, and its `repr` is the
§30 text: the expected row, "No matching row found.", and every actual row as a tuple of
values. On success it reprs as `Matched row 2` so a passing assertion reads normally.

`src/django_admin_kit/pages.py`: `ChangelistPage.contains(pattern)`.

`tests/test_matching.py` (new, no browser, fake rows): a matching literal row; `""` matches
an empty cell and nothing else; a wrong value, a wrong length; the failure repr contains
"Expected row", the pattern and every actual row.
`tests/test_rows.py`: `page.contains(("Bolt", "SKU-Bolt", Decimal("10.00"), True, ...))`;
`pytest.raises(AssertionError)` around `assert page.contains(("Nobody", ...))` checking the
message reaches pytest's output.

Spec: §9 intro's first example minus the sentinel and the callable; §9.2 and §9.3 `(done)`;
§30 changelist part `# done`.

Consistency: additive; nothing else calls `matches`.

Commit: `Match one changelist row against literal values with a readable failure`.

### R7. The sentinels `ANY` and `ANY_ROW`

`src/django_admin_kit/matching.py`: `ANY` (matches any cell) and `ANY_ROW` (matches any row)
as plain objects whose `repr` is their name, importable from `django_admin_kit.matching`;
`matches` honours both. The failure text prints them by name.

`tests/test_matching.py`: `ANY` in a tuple; `ANY_ROW` against an empty row list fails and
against any row passes; the failure repr shows `ANY` in the expected row.
`tests/test_rows.py`: `page.contains(("Bolt", ANY, ANY, ANY, ...))`, `page.contains(ANY_ROW)`
on three products, and on an empty changelist it fails.

Spec: §9.4 and §9.6 (single-pattern part) `(done)`; §9.1 sentinels bullet.

Consistency: additive to R6's matcher.

Commit: `Let ANY stand for any cell and ANY_ROW for any row in a changelist pattern`.

### R8. Callable cell matchers

`src/django_admin_kit/matching.py`: a callable in a pattern is called as `matcher(row,
cell)` and its truthiness decides; an exception inside it propagates unchanged, so a test
sees its own bug. The failure text shows a callable by its `__name__` (or `<lambda>`).

`tests/test_matching.py`: a callable that passes, one that fails, one that reads
`row["email"]` and `cell.links`; the failure repr names the callable.
`tests/test_rows.py`: `page.contains(("Bolt", ANY, lambda row, cell: cell.value > 5, ...))`
and a callable on `links[0].target`.

Spec: §9.5 `(done)`; §9.1 callables bullet; §9 intro's first example complete `# done`.

Consistency: additive.

Commit: `Match a changelist cell with a callable that receives the row and the cell`.

### R9. Column-addressed patterns

`src/django_admin_kit/matching.py`: a dictionary pattern matches by column name, unlisted
columns unconstrained, values being the same cell patterns; an unknown column name raises
`KeyError` naming it and the row's columns rather than silently not matching. The failure
text prints the dictionary and, for each actual row, the listed columns only.

`tests/test_matching.py`: a dict with a literal, `ANY` and a callable; an unknown key raises;
the failure repr shows the listed columns.
`tests/test_rows.py`: `page.contains({"name": "Nut", "is_active": True})`.

Spec: §9.7 dictionary example `# done`; §9.1 `(done)`.

Consistency: additive.

Commit: `Match a changelist row by a few named columns instead of every cell`.

### R10. `contains` with a collection of rows

`src/django_admin_kit/matching.py`: collection detection per decision 12; each pattern must
take a different row, in any order, found by backtracking (decision 11). The failure text
says which pattern found no row of its own and prints the actual rows.

`src/django_admin_kit/pages.py`: `contains` accepts a collection.

`tests/test_matching.py`: two patterns in the wrong order pass; a collection where greedy
assignment would fail (`[ANY_ROW, ("Jane", ...)]` against `[Jane, John]`) passes;
`[ANY_ROW, ANY_ROW]` against one row fails; `[]` passes; a list of literals is one row,
not a collection; the failure repr names the pattern without a row.
`tests/test_rows.py`: `page.contains([{"name": "Washer"}, ("Bolt", ANY, ...)])`.

Spec: §9 intro collection example `# done`; §9.6 collection sentence.

Consistency: a single pattern behaves as in R6 to R9.

Commit: `Match a collection of changelist rows in any order, each to a row of its own`.

### R11. `match`: the whole changelist in order

`src/django_admin_kit/matching.py`: positional check, count must equal; `ANY_ROW` holds a
position; a single pattern means exactly one row. The failure text says "expected N rows,
found M" or "row N did not match" with the pattern and the row.

`src/django_admin_kit/pages.py`: `ChangelistPage.match`.

`tests/test_matching.py`: right order passes, wrong order fails, wrong count fails,
`ANY_ROW` at a position, `match(pattern)` with two rows fails, `match([])` on no rows
passes; the failure repr names the position.
`tests/test_rows.py`: `page.match([...])` on the three products in the admin's order with
one `ANY_ROW`.

Spec: §9 heading `(done)` and the `match` examples; §9.9 `(done)`; §26 changelist
examples `# done`; §32 item 9 `(done)`; §1 bullet on row contents.

README: one entry "Reading and matching changelist rows" with `rows[0]["price"].value`,
`links`, `contains`, `match`.

Consistency: additive; `contains` is untouched.

Commit: `Match the whole changelist in order with match()`.

### After all slices

`pytest -n 4`, `ruff check`, `ruff format --check`, `mypy`, `tox -e 3.8-dj32,3.12-dj61`, and
because R4 and R5 touch locale-sensitive code, `tox -m full` once before the pull request. Verify
every mark, delete this file.

## 7. Review notes

**R1. Resolved:** the row without a change link comes from a second model, `Category`,
rather than from touching `ops_site` (decision 14).

**R2. Resolved:** every numeric type reaches a real page through `quantity` (`int`),
`price` (`Decimal`) and `weight` (`float`), appended to `list_display` so existing columns
do not move; the unit tests carry the exhaustive cases (decision 14, slice R4).

**R3. Agreed:** `display_for_field` renders a choice as its label, and the text rule
returns it as text, which is what §28.3 calls "the display value of a choice". No `choice`
rule is needed for changelists; the entry in §28.3's list stays for form fields (§13.3).
Nothing to build here, noted so it is not read as an omission.

**R4. Resolved:** the parser accepts every character of Django's format language (decision
4), and a text that does not fit its format leaves the value as text with a warning
(decision 5).

**R5. Agreed:** decision 2: the page's precision wins. A test that creates
`timezone.now()` and compares the cell to it will fail on seconds. The README entry says so
in one sentence.

**R6. Resolved:** `ANY` and `ANY_ROW` live in `django_admin_kit.matching`.

**R7. Resolved:** all three `empty_value_display` levels are honoured (decision 7), through
a helper that uses `AdminSite.get_model_admin` from Django 5.1 and the registry before it.
