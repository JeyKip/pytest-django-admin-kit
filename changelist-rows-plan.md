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
* `Cell`: `value` (typed, per §3.4), `links` (list of `(text, target)` pairs with `.text` and
  `.target`), `native`.
* Normalization of a cell's value: boolean icon to `True`/`False`/`None`; the site's empty
  value to `""`; integer, decimal and float fields to `int`, `Decimal`, `float`; date, time
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
  it; see decision 4.
* A `ModelAdmin`-level or field-level `empty_value_display`. The site's value is honoured;
  see decision 6.
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
| Test project | `tests/project/shop/models.py`, `admin.py` | `Product` with name, sku, price, is_active, released_on; `ProductAdmin` with `price_with_tax` | a `DateTimeField`, a nullable boolean, a two-link column |

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
   expression using the translated names of fact 5, and refuses loudly a format character
   it does not support (time zone names and offsets, ISO week numbers), naming the character
   and the format. Supported: `d j m n F M N b E y Y H G h g i s u A a P f D l S` and escaped
   literals; that covers every `DATE_FORMAT`, `DATETIME_FORMAT` and `TIME_FORMAT` shipped in
   `django/conf/locale`.
5. **Numbers are parsed with the project's separators.** The thousand separator is removed
   only when `USE_THOUSAND_SEPARATOR` is on, the decimal separator becomes `.`, and the field
   type decides `int`, `Decimal` or `float`. `page.count` uses the same rule.
6. **The empty value is the site's.** `site.empty_value_display` is public on every version;
   the `ModelAdmin`'s is reachable publicly only from 5.1. A project that overrides it on a
   `ModelAdmin` gets `"-"`-style text back until it replaces the `empty` rule under §28.3.
7. **A link target is its path.** The `href` is passed through the same rule as
   `destination` (`urlsplit(...).path`), so `?_changelist_filters=...` and an absolute form
   both compare equal to `admin_ui.url.edit(obj)`. That is the §6.3 paragraph.
8. **`row.object` comes from the change link.** `resolve(target)` on the first link whose
   path resolves to the model's change view gives `object_id`; the instance is fetched with
   `model._default_manager.get(pk=...)`. A row without such a link has `object` `None`.
9. **`contains` and `match` return a result object, not a bare bool.** It is falsy when the
   match failed and its `repr` is the §30 text (expected pattern, actual rows, and for
   `match` which position failed). `assert page.contains(...)` then prints that text through
   pytest's ordinary assertion rewriting, with no hook. A truthy result reprs as `True`-like
   text so a passing assertion reads normally.
10. **A collection matches distinct rows, in any order, by backtracking.** Each pattern must
    take a different row; greedy assignment would fail `[ANY_ROW, ("Jane", ...)]` against
    `[Jane, John]`. Changelists are at most one page, so the search is cheap.
11. **A list is a collection when every element is a row pattern** (tuple, list, dict,
    `ANY_ROW`); otherwise it is one row. `[]` is an empty collection: `contains([])` is true,
    `match([])` means no rows.
12. **The sentinels are plain objects with a `repr`.** With `.values` gone from the spec they
    never meet `==`, so no `__eq__`.
13. **The test project gains what the rules need**: `Product.created_at` (`DateTimeField`),
    `Product.featured` (`BooleanField(null=True)`) for the unknown icon, and a `documents`
    method column rendering two links. The migration is regenerated with the command in the
    README. Existing header and column assertions in `tests/test_changelist.py` are extended
    with the new columns.
14. **Branch:** `feature/changelist-rows`, already holding the spec changes. This plan file
    is committed on the branch while it is being refined and removed once every slice is in.

## 5. Field validation rules

Not applicable to the package: no settings, serializers or writable fields are added. The test
project's new model fields are fixtures for the suite (`created_at` with an explicit value in
every test that reads it, `featured` nullable, default `None`).

## 6. Commit plan

### R1. Read the rows and cells of a changelist as text

`src/django_admin_kit/rows.py` (new): `Cell` (`value` as text for now, `native`, `_name`,
`_field`), `Row` (`__getitem__` by name or position, `index`, `native`, `_cells` built from
`tr > th, tr > td` minus `.action-checkbox` and `page.columns`). A missing name raises
`KeyError` naming it and listing the row's columns, as `models_for` does.

`src/django_admin_kit/pages.py`: `ChangelistPage.rows` (cached, through `_shown()`, `[]`
when there is no table); the page keeps the model it was opened for.

`src/django_admin_kit/session.py`: `list()` hands the model to the page.

`tests/test_rows.py` (new): a viewer reads `page.rows[0]["name"].value == "Bolt"`, by
position, `row.index`, `len(page.rows) == 3` in the admin's order; an unknown column raises;
an empty changelist has `rows == []`; a refused page raises on `rows`; `row.native` and
`cell.native` are Playwright locators (`cell.native.text_content()`).

`tests/test_changelist.py`: the "did not open" test gains `rows`.

Spec: §8.2 `page.rows == []` `# done`; §3.5 examples `# done` for rows and cells; §3.6
`page.rows[0].native` and `page.rows[0]["email"].native` `# done`.

Consistency: `rows` is new; nothing reads it yet.

Commit: `Read the rows and cells of a changelist by column name and position`.

### R2. Normalize boolean icons and the empty value

`src/django_admin_kit/normalize.py` (new): the rule table with `boolean` (icon `alt` to
`True`/`False`/`None`), `empty` (text equal to the site's `empty_value_display` to `""`) and
`text`; `Cell.value` runs the table.

Test project: `Product.featured = BooleanField(null=True)` in `list_display`; migration.

`tests/test_rows.py`: `is_active` reads `True`/`False`; `featured` reads `None` when unset;
`released_on` unset reads `""`; a method column returning a bool without `boolean=True` reads
`"True"` as text (what the user sees).

Spec: §3.4 first two bullets `(done)`; §9.8 boolean example `# done`; §32 item 10's boolean
and empty parts noted in the plan, the item marked when links land.

Consistency: text cells are unchanged; only icon and `-` cells change value.

Commit: `Normalize boolean icons and the empty value in changelist cells`.

### R3. Links on a cell, targets as paths, and the object behind a row

`src/django_admin_kit/rows.py`: `Link = NamedTuple(text, target)`; `Cell.links` from `a`
elements, targets through the `destination` path rule; `Row.object` per decision 8.

Test project: `ProductAdmin.documents` renders two links; `list_display` extended.

`tests/test_rows.py`: the `name` cell's `links == [("Bolt", admin_ui.url.edit(bolt))]`; a
plain cell's `links == []`; `documents` gives two pairs and `.target` reads the second; a
target with `_changelist_filters` (open the list with `?is_active__exact=1`) still compares
equal; `row.object == bolt`; `row.object is None` on the ops site with `list_display_links =
None` (add that `ModelAdmin` to `tests/project/ops.py`).

Spec: §3.4 links bullet `(done)`; §6.3 link paragraph `(done)`; §9.8 links examples `# done`;
§32 item 10 `(done)`.

Consistency: additive.

Commit: `Expose a cell's links with normalized targets and the object behind a row`.

### R4. Typed numbers, and the count through the same rule

`src/django_admin_kit/normalize.py`: `number` rule for `IntegerField`, `DecimalField`,
`FloatField` (and their subclasses: `AutoField`, `BigIntegerField`, `PositiveIntegerField`),
using `get_format("DECIMAL_SEPARATOR")`, `get_format("THOUSAND_SEPARATOR")` and
`USE_THOUSAND_SEPARATOR`. `ChangelistPage.count` parses through it; the stopgap comment goes.

`tests/test_rows.py`: `price` reads `Decimal("10.00")`; `id` would read `int` (add `id` to
`list_display`? no: assert on `price` and on a `PositiveIntegerField`? Product has none; keep
to `price` and a unit test). `tests/test_normalize.py` (new, no browser): the number rule
under `en`, `de` (`1.234,56`) and `fr` (non-breaking space), with `override_settings`.

Spec: §3.4 numbers half of the bullet; §9.8 example `"10.00"` becomes `Decimal("10.00")`.

Consistency: cells of numeric fields change type; nothing in the suite compared one yet.

Commit: `Normalize numeric cells through the project's number formats`.

### R5. Dates and times

`src/django_admin_kit/dateformats.py` (new): `parse(text, format) -> datetime` (with a
flag for what was present), the inverse of `django.utils.dateformat` per decision 4.
`tests/test_dateformats.py` (new, no browser): round trips through `dateformat.format` for
every shipped locale's `DATE_FORMAT`, `DATETIME_FORMAT`, `TIME_FORMAT` on a few values,
under `translation.override`; midnight and noon under `P`; an unsupported character raises
naming it.

`src/django_admin_kit/normalize.py`: `datetime` rule: `DateField` to `date`, `TimeField` to
`time`, `DateTimeField` to an aware datetime in `settings.TIME_ZONE`.

Test project: `Product.created_at = DateTimeField()` in `list_display`; migration.

`tests/test_rows.py`: `released_on` reads `date(2026, 1, 1)`; `created_at` created as
`datetime(2026, 1, 1, 15, 30, tzinfo=utc)` reads equal (project zone is UTC); a second test
under `override_settings(TIME_ZONE="Europe/Kyiv")` still reads equal (aware comparison) and
`.hour == 17`.

Spec: §3.4 dates/times bullet `(done)`; §31 "Values render through the formats and time zone
the project has configured" `(done)`.

Consistency: additive rule; date cells were text before.

Commit: `Normalize date and time cells by inverting the project's date formats`.

### R6. `contains` with one pattern, the sentinels, callables, and the failure text

`src/django_admin_kit/matching.py` (new): `ANY`, `ANY_ROW`; `matches(pattern, row)` for
tuple/list (length must equal the row's cell count), dict (by column name), `ANY_ROW`;
cell match: literal `==`, `ANY`, callable `(row, cell)`; `MatchResult` per decision 9 with
the §30 text. Public names importable from `django_admin_kit.matching`.

`src/django_admin_kit/pages.py`: `ChangelistPage.contains(pattern)`.

`tests/test_matching.py` (new, no browser, fake rows): literals, `""`, `ANY`, callables,
dict with unlisted columns, `ANY_ROW`, a tuple of the wrong length is no match, and the
failure repr contains "Expected row", the pattern and every actual row.
`tests/test_rows.py`: `page.contains(("Bolt", "SKU-Bolt", Decimal("10.00"), True, ...))`,
`page.contains({"name": "Nut"})`, `page.contains(ANY_ROW)`, a failing `contains` on a
viewer's page; `pytest.raises(AssertionError)` around `assert page.contains(...)` checking
the message.

Spec: §9 intro single-pattern example, §9.1 to §9.7 (dict example), §9.8 pattern examples,
§30 changelist part `# done`.

Consistency: additive.

Commit: `Match one changelist row against literals, ANY, ANY_ROW and callables`.

### R7. Collections and `match`

`src/django_admin_kit/matching.py`: collection detection (decision 11), backtracking
assignment for `contains([...])`, positional check for `match([...])`, `match(pattern)` as
"exactly one row"; `MatchResult` text for "no row for pattern N" and "row N did not match".

`src/django_admin_kit/pages.py`: `contains` accepts a collection; `match` added.

`tests/test_matching.py`: a collection where greedy assignment would fail, distinctness
(`[ANY_ROW, ANY_ROW]` against one row fails), `match` with a wrong count, wrong order, and
`ANY_ROW` holding a position, `match(pattern)` with two rows fails.
`tests/test_rows.py`: `page.match([...])` on the three products in the admin's order with
one `ANY_ROW`, `page.contains([...])` in the wrong order passes.

Spec: §9 heading `(done)` and remaining examples; §9.9 `(done)`; §26 changelist examples
`# done`; §32 item 9 `(done)`; §1 bullet on row contents; §25 unchanged.

README: one entry "Reading and matching changelist rows" with `rows[0]["price"].value`,
`links`, `contains`, `match`.

Consistency: `contains` with a single pattern behaves as in R6.

Commit: `Match a collection of rows in any order, and the whole changelist in order`.

### After all slices

`pytest -n 4`, `ruff check`, `ruff format --check`, `mypy`, `tox -e 3.8-dj32,3.12-dj61`, and
because R5 touches locale-sensitive code, `tox -m full` once before the pull request. Verify
every mark, delete this file.

## 7. Review notes

**R1. `row.object` and the ops site.** Proving `object is None` needs a `ModelAdmin` with
`list_display_links = None` somewhere; the plan puts it on `ops_site`, whose docstring says
its job is URL resolution. Alternative: a second `ModelAdmin` for `Product` is impossible on
one site, so either extend `ops.py`'s stated purpose or skip that one test. Recommended:
extend `ops.py`, one line in its docstring.

**R2. `id` as a typed cell.** `ProductAdmin` does not list `id`; the `int` case is covered by
the no-browser rule test rather than a page. Adding `id` to `list_display` would show it and
cost every header test one more entry. Recommended: leave it to the unit test.

**R3. Choice fields.** `display_for_field` renders a choice as its label, and the text rule
returns it as text, which is what §28.3 calls "the display value of a choice". No `choice`
rule is needed for changelists; the entry in §28.3's list stays for form fields (§13.3).
Nothing to build here, noted so it is not read as an omission.

**R4. The parser's scope.** Decision 4 lists the supported format characters; formats a
project sets itself may use others (`e`, `T`, `O`, `c`, `r`, `U`, `W`, `z`). The rule raises
naming the character, and the `datetime` rule can be replaced under §28.3 once it exists.
Alternative: fall back to text silently for such a format. Recommended: raise; a silent text
value in a typed column is the kind of surprise §3.4 exists to prevent.

**R5. Seconds and microseconds.** Decision 2: the page's precision wins. A test that creates
`timezone.now()` and compares the cell to it will fail on seconds. The README entry says so
in one sentence.

**R6. Where `ANY` and `ANY_ROW` live.** `django_admin_kit.matching`, per §27's rule that
public names are imported from the module that defines them. Alternative: also re-export
from the package root; §27 forbids it (startup cost). Recommended: `matching`.
