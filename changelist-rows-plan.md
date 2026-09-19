# Changelist rows: reading cells, normalizing values, matching rows

Implements specification §9 (Changelist Row Matching) in full, and the parts of other
sections without which §9 cannot be marked done:

* §3.4 normalized values for changelist cells: booleans drawn as icons, links, text;
* §3.5 addressing of rows and cells, and §3.6 native handles on `Row` and `Cell`;
* §6.3, the paragraph on links read from a page;
* §8.2, the `page.rows == []` line;
* §30, the failure output of a row match;
* §32 criteria 9 and 10.

## 1. Scope

Built:

* `page.rows`: a list of `Row`, in the order shown; `[]` on an empty changelist; raises on a
  changelist that did not open, like every other reader.
* `Row`: `row["email"]` and `row[2]` give a `Cell`; `row.index`, `row.native`, `row.object`.
* `Cell`: `value` (normalized, per §3.4), `text` (what the document shows, before
  normalization), `links` (list of `Link` objects with `.text` and `.href` as a split URL,
  each comparing equal to a `(text, href)` pair), `native`.
* Normalization of a cell's value: the boolean icon to `True`/`False`/`None`; everything
  else to the text shown, so a date, a number or the admin's empty value reads exactly as
  the user sees it in the locale the browser is pinned to.
* `page.contains(pattern)` for one row and `page.match([patterns])` for the whole
  changelist; the sentinels `ANY` and `ANY_ROW`; callables `matcher(row, cell)`; `Link`
  patterns; tuple, list and dictionary patterns.
* A failing `assert page.contains(...)` prints the expected pattern and the actual rows, as
  §30 shows, through pytest's ordinary assertion output.
* `page.count` reads its number through `normalize.integer`, proven against what Django
  renders under a grouping locale.
* Spec marks, README, tests, and additions to the test project's `Product` and its admin.

Out of scope:

* The settings surface of §28.3 (`DJANGO_ADMIN_KIT["normalizers"]`, `admin_ui.normalizer(...)`).
  The rules are built as one replaceable table so that §28.3 only has to read settings into
  it; see decision 2. Typed dates and numbers are what a project puts in the `datetime` and
  `number` slots there.
* `list_editable` cells, and every other changelist interaction of §33 (1.2.0).
* Form fields (§10 onwards). `links` on a rendered-only field (§13.4) reuses `Cell`'s
  pair type when it is built.

## 2. Where the change goes

| Layer | File | What exists | What this adds |
|---|---|---|---|
| Session | `src/django_admin_kit/session.py` | `list(model)` via `_open()` | passes the model to the page |
| Page | `src/django_admin_kit/pages.py` | `ChangelistPage` with `count`, `headers`, `columns`, `_header_cells`, `_shown()`, `_text()`, `_token()` | `rows`, `contains`, `match`; a `ModelPage` base that keeps the model, for every page opened for one |
| Rows | `src/django_admin_kit/rows.py` (new) | | `Row`, `Cell`, `Link` |
| Normalization | `src/django_admin_kit/normalize.py` (new) | | the rule table, each rule, `integer` |
| Matching | `src/django_admin_kit/matching.py` (new) | | `ANY`, `ANY_ROW`, pattern matching, the failure text |
| Test project | `tests/project/shop/models.py`, `admin.py` | `Product` with name, sku, price, is_active, released_on; `ProductAdmin` with `price_with_tax` | a nullable boolean, a bool the admin renders as text, an `empty_value_display` on the admin, a two-link column; a `Category` model whose admin has no change links |

Reused as is: `_shown()` for the guard, `_text()` for text, `_token()` for the `field-<name>`
class, `page.columns` for the column order, `AdminUrls` and the `destination` path rule for
links, `apps.get_model` style public lookups (`model._meta.get_field`), and the
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
   matrix) renders a `BooleanField` as `<img alt="True|False|None">` (`icon-yes`,
   `icon-no`, `icon-unknown`), and anything it does not know through `display_for_value`,
   which renders a `bool` returned by a method column as text unless the method sets
   `boolean = True`, in which case as the icon. Everything else is text: a date through
   the project's `DATE_FORMAT`, a number through `number_format`, `None` as the empty value
   display, a `FileField` as a link.
4. The paginator's count is rendered through the template engine, which groups it with the
   project's `THOUSAND_SEPARATOR` when `USE_THOUSAND_SEPARATOR` is on (`,` under `en`, a
   non-breaking space under `fr`).
5. The same live server thread and the test process share settings, so the text the page
   was rendered with is the text the project's formats produce in the test, as long as the
   language is the same: the browser locale is pinned to `LANGUAGE_CODE` (§28.4), and the
   test process runs with `LANGUAGE_CODE` active.

## 4. Decisions

1. **A cell is text unless the admin drew something else.** `value` is the document's text,
   whitespace collapsed, except where the admin rendered an icon (a boolean) or a link (the
   text, with the link kept separately). A date, a number or the empty value display is
   text, compared as the user reads it; a test that covers several locales parametrizes the
   locale and the expected rendering. This keeps the package out of the business of parsing
   Django's format language back, and keeps every assertion about what is on the page.
2. **Rules are a table, tried in order, first answer wins.** Each rule is a function
   `(cell, column) -> value` returning a private `NOT_HANDLED` marker to pass. The table is
   a module-level dict keyed by the names §28.3 lists, so that section can replace entries
   from settings without restructuring. This plan builds the entries that do something:
   `boolean`, `link` (for `links`, not `value`) and `text`. The other slots §28.3 names
   (`empty`, `datetime`, `number`, `choice`) default to the text shown, so they change
   nothing until a project replaces one; they are added by the §28.3 slice together with the
   settings that replace them, routed by the model field behind the column (decision 3) so a project's `datetime`
   rule only ever sees the cells of date, time and datetime fields. Until then the table is
   not public.
3. **The model field behind a column arrives with the slots that need it.** The
   `datetime`, `number` and `choice` slots of §28.3 are applied by field type, so a rule a
   project puts there sees only its kind of cell; that takes `model._meta.get_field(name)`
   (or `None` for a computed column, `FieldDoesNotExist`) on the cell's column. Nothing in
   this plan reads it, so it is built by the §28.3 slice, not here. `Cell.column` is the
   configured name until then. This needs no `ModelAdmin` and no private attribute.
4. **`page.count` is an integer, read the way an integer is grouped.** The locale-aware parse
   of a grouped integer is "remove the grouping separator, then `int()`", and dropping every
   non-digit does exactly that in every locale, including the non-breaking space `fr` uses
   (which the whitespace collapsing in `_count_line` has already turned into a plain space).
   The parse lives in `normalize.integer`, and its unit tests render their input with
   `django.utils.formats.number_format` under `en` and `fr` with `USE_THOUSAND_SEPARATOR`
   on, so the claim is proven against Django rather than against typed literals.
5. **A link is its text and its `href` as rendered, split.** `Link(text, href)` accepts
   `href` as a string or a `SplitResult` and keeps it as a `SplitResult`, so a test reaches
   `.path`, `.query`, `.netloc` and the rest by their standard names, and compares the path
   against `admin_ui.url` where that is what it means. Nothing is normalized away: a
   filtered changelist's `_changelist_filters` is in the query, as the user's browser sees
   it. `Link` is a small class, not a tuple, and compares equal to another `Link` and to a
   `(text, href)` pair with either `href` type, so `links == [("Bolt", "/admin/.../change/")]`
   holds. It is the one place the package implements comparison behaviour, per §3.1. A
   plain `list[Link]` compares element-wise through it, so no list class is needed. In a
   pattern a link is spelled `Link(...)`, never guessed from a pair; a cell pattern matches
   when it equals the cell's value or the cell's links, so a project whose own rule puts
   links into `value` needs nothing else.
6. **`row.object` comes from the change link.** `resolve(href.path)` on the first link
   whose path resolves to the model's change view gives `object_id`; the instance is fetched with
   `model._default_manager.get(pk=...)`. A row without such a link has `object` `None`.
7. **`contains` and `match` raise on failure and return `True` on success.** Pytest's
   rewriting has no hook for a bare `assert x`: it passes the value through `saferepr`,
   which escapes newlines, truncates at 240 characters and prints the repr twice, so a
   falsy result object cannot produce the §30 text. An `AssertionError` whose message is
   that text can: pytest prints an exception message line by line, which is how every
   assertion helper (`assertEqual`, `assert_frame_equal`) shows its picture. `assert
   page.contains(...)` reads as before; the `assert` is not what fails. The absence of a row
   is asserted against `page.rows` or `page.count`.
8. **`contains` takes one row; `match` takes the rows.** A collection form of `contains`
   (several patterns, each on a row of its own, in any order) was built and withdrawn: it
   needed a rule to tell a collection from a row, and that rule had a corner (a row whose
   every cell is a list of links) that had to be explained away. One `contains` per
   expected row is the same number of lines and fails one row at a time; `match` covers
   "exactly these, in order", with `ANY_ROW` for positions a test does not care about. Any
   tuple or list given to `contains` is therefore one row, and `match` always receives a
   list or tuple of rows, `[]` meaning no rows.
9. **The sentinels are plain objects with a `repr`.** With `.values` gone from the spec they
   never meet `==`, so no `__eq__`.
10. **The test project gains what the rules need**: `Product.featured`
    (`BooleanField(null=True, blank=True)`) for the unknown icon, a `ProductAdmin.is_released`
    method returning a bool without `boolean=True`, so the suite shows a bool the admin
    renders as text, `ProductAdmin.empty_value_display = "(none)"`, so an empty cell reads
    a configured text rather than the site's `"-"`, a `documents` method column rendering
    two links, and a second model, `Category(name)`, registered on the default site with
    `list_display_links = None`, for a row that links to nothing. The spec's own examples
    already name `Category` next to `Product`. The migration is regenerated with the command
    in the README. Existing header and column assertions in `tests/test_changelist.py` are
    extended with the new columns, and `tests/test_index.py` gains `Category` in the default
    site's lists.
11. **Branch:** `feature/changelist-rows`, already holding the spec changes. This plan file
    is committed on the branch while it is being refined and removed once every slice is in.

## 5. Field validation rules

Not applicable to the package: no settings, serializers or writable fields are added. The test
project's new model field is a fixture for the suite (`featured` nullable, default `None`).

## 6. Commit plan

### R1. Read the rows and cells of a changelist as text (done)

`src/django_admin_kit/rows.py` (new): `Cell` (`text` as the document's whitespace-collapsed
text, `value` equal to it for now, `native`), `Row` (`__getitem__` by name or position,
`index`, `native`, `_cells` built from `tr > th, tr > td` minus `.action-checkbox` and
`page.columns`). A missing name raises `KeyError` naming it and listing the row's columns.

`src/django_admin_kit/pages.py`: `ChangelistPage.rows` (cached, through `_shown()`, `[]`
when there is no table).

`tests/test_rows.py` (new): a viewer reads `page.rows[0]["name"].value == "Bolt"` and
`.text == "Bolt"`, by position, `row.index`, `len(page.rows) == 3` in the admin's order; an
unknown column raises; an empty changelist has `rows == []`; a refused page raises on
`rows`; `row.native` and `cell.native` are Playwright locators.

`tests/test_changelist.py`: the "did not open" test gains `rows`.

Spec: §8.2 `page.rows == []` `# done`; §3.5 examples `# done` for rows and cells; §3.6
`page.rows[0].native` and `page.rows[0]["email"].native` `# done`.

Commit: `Read the rows and cells of a changelist by column name and position`.

### R2. Normalize boolean icons, and the count through `integer` (done)

`src/django_admin_kit/normalize.py` (new): the rule table with `boolean` (one `img[alt]` in
a cell with no text, `alt` to `True`/`False`/`None`) and `text`; `normalize(cell, column)`;
`integer(text)` per decision 4. `Cell.value` runs the table, cached; `Cell` knows its
column name so a rule can name it. `ChangelistPage.count` calls `integer`; the stopgap
comment in `_count_line` goes.

Test project: `Product.featured` in `list_display`; migration. `ProductAdmin.is_released`
and `ProductAdmin.empty_value_display = "(none)"` per decision 10.

`tests/test_rows.py`: `is_active` reads `True`/`False`; `featured` reads `None` when unset
and its `text` is `""`; `is_released` reads `"False"` as text (what the user sees) and
`"True"` once a date is set; an unset `released_on` reads `"(none)"` as both `value` and
`text`. `tests/test_changelist.py`: headers and columns gain `"Featured"` / `"featured"`
and `"Released"` / `"is_released"`. `tests/test_changelist_count.py`: cases whose text is
`number_format(1000, use_l10n=True)` under `en` and `fr` with `USE_THOUSAND_SEPARATOR` on,
read back as `1000`.

Spec: §3.4 first bullet `(done)`; §9.8 boolean and empty examples `# done`; §9.3 `(done)`;
§32 item 10's boolean part noted here, the item marked when links land.

Consistency: text cells are unchanged; only icon cells change value. `count` reads the same
numbers it did.

Commit: `Normalize boolean icons in changelist cells`.

### R3. Links on a cell, and the object behind a row

`src/django_admin_kit/rows.py`: `Link` (`text`, `href` as a `SplitResult`; equal to a
`Link` or a `(text, href)` pair with `href` a string or split) per decision 5; `Cell.links`
from `a` elements;
`Row.object` per decision 6, which needs the model the page was opened for. `pages.py`
gains `ModelPage(AdminPage)`, taking the model, as the base of the changelist, create,
edit and delete pages; `session.py` hands each its model (`type(instance)` for the
last two).

Test project: `ProductAdmin.documents` renders two links; `list_display` extended;
`Category` model and `CategoryAdmin(list_display=("name",), list_display_links=None)`;
migration. `tests/test_index.py`: the superuser's lists gain `Category` before `Product`.

`tests/test_rows.py`: the `name` cell's `links == [("Bolt", admin_ui.url.edit(bolt))]` and
`links[0].href.path == admin_ui.url.edit(bolt)`; a plain cell's `links == []`; `documents`
gives two pairs, compared as strings and as split URLs; with the `is_active` filter
applied, `links[0].href.path` still equals `admin_ui.url.edit(bolt)` while `href.query`
carries `_changelist_filters` and the pair no longer matches; `row.object == bolt`;
`row.object is None` on the `Category` changelist, whose admin has `list_display_links =
None`, and its `name` cell has `links == []`. `tests/test_links.py` (new, no browser):
`Link` equality with a `Link`, a pair with a string, a pair with a split URL, a different
href, a different text, a plain string (never equal); a list of links against a list of
pairs; `repr`.

Spec: §3.4 links bullet `(done)`; §6.3 link paragraph and example `(done)`; §9.8 links
examples `# done`; §32 item 10 `(done)`.

Consistency: additive.

Commit: `Expose a cell's links as rendered and the object behind a row`.

### R4. `contains` with one literal row, and the failure text

`src/django_admin_kit/matching.py` (new): `matches(pattern, row)` for a tuple or list of
literals, one per cell, compared with `==` against `cell.value`; a pattern of the wrong
length is no match. `contains(rows, pattern)` returns `True` or raises `AssertionError`
per decision 7 with the §30 text: the expected row, "No matching row found.", and every
actual row as a tuple of values.

`src/django_admin_kit/pages.py`: `ChangelistPage.contains(pattern)`.

`tests/test_matching.py` (new, no browser, fake rows): a matching literal row; `""` matches
an empty cell and nothing else; a wrong value, a wrong length; the failure message contains
"Expected row", the pattern and every actual row, on separate lines.
`tests/test_rows.py`: `page.contains(("Bolt", "SKU-Bolt", "10.00", True, ...))`;
`pytest.raises(AssertionError)` around `page.contains(("Nobody", ...))` checking the
message shows the actual rows.

Spec: §9 intro's first example minus the sentinel and the callable; §9.2 and §9.3 `(done)`;
§30 changelist part `# done`.

Consistency: additive; nothing else calls `matches`.

Commit: `Match one changelist row against literal values with a readable failure`.

### R5. Match a cell by its links

`src/django_admin_kit/matching.py`: a cell pattern matches when `cell.links == [it]`, when
it is a list or tuple and `cell.links == list(it)`, or when it equals `cell.value`; the
comparison is `Link.__eq__`'s (decision 5), and nothing is guessed from shape. The failure
text prints the pattern as the user wrote it and, where the pattern is or holds a `Link`,
a cell's links as `Link`s.

`tests/test_matching.py`: a `Link` against a one-link cell, with a string and with a split
href; a `Link` against a plain cell fails; a list and a tuple of two `Link`s against a
two-link cell, and in the wrong order fails; `[]` matches a cell without links; a bare pair
is a literal.
`tests/test_rows.py`: `page.contains((Link("Bolt", admin_ui.url.edit(bolt)), "SKU-Bolt", ...))`
and a row pattern with `[Link("Datasheet", ...), Link("Manual", ...)]` in the `documents`
position.

Spec: §9.1 links bullet `(done)`; §9.8 pattern examples `# done`.

Consistency: additive; a cell pattern that is not a pair matches as in R4.

Commit: `Match a changelist cell by the links it renders`.

### R6. The sentinels `ANY` and `ANY_ROW`

`src/django_admin_kit/matching.py`: `ANY` (matches any cell) and `ANY_ROW` (matches any row)
as plain objects whose `repr` is their name, importable from `django_admin_kit.matching`;
`matches` honours both. The failure text prints them by name.

`tests/test_matching.py`: `ANY` in a tuple; `ANY_ROW` against an empty row list fails and
against any row passes; the failure message shows `ANY` in the expected row.
`tests/test_rows.py`: `page.contains(("Bolt", ANY, ANY, ANY, ...))`, `page.contains(ANY_ROW)`
on three products, and on an empty changelist it fails.

Spec: §9.4 and §9.6 (single-pattern part) `(done)`; §9.1 sentinels bullet.

Consistency: additive to R4's matcher.

Commit: `Let ANY stand for any cell and ANY_ROW for any row in a changelist pattern`.

### R7. Callable cell matchers

`src/django_admin_kit/matching.py`: a callable in a pattern is called as `matcher(row,
cell)` and its truthiness decides; an exception inside it propagates unchanged, so a test
sees its own bug. The failure text shows a callable by its `__name__` (or `<lambda>`).

`tests/test_matching.py`: a callable that passes, one that fails, one that reads
`row["email"]` and `cell.links`; the failure message names the callable.
`tests/test_rows.py`: `page.contains(("Bolt", lambda row, cell: cell.value.startswith("SKU-"), ...))`
and a callable on `links[0].href.path`.

Spec: §9.5 `(done)`; §9.1 callables bullet; §9 intro's first example complete `# done`.

Consistency: additive.

Commit: `Match a changelist cell with a callable that receives the row and the cell`.

### R8. Column-addressed patterns

`src/django_admin_kit/matching.py`: a dictionary pattern matches by column name, unlisted
columns unconstrained, values being the same cell patterns; an unknown column name raises
`KeyError` naming it and the row's columns rather than silently not matching. The failure
text prints the dictionary and, for each actual row, the listed columns only.

`tests/test_matching.py`: a dict with a literal, `ANY` and a callable; an unknown key raises;
the failure message shows the listed columns.
`tests/test_rows.py`: `page.contains({"name": "Nut", "is_active": True})`.

Spec: §9.7 dictionary example `# done`; §9.1 `(done)`.

Consistency: additive.

Commit: `Match a changelist row by a few named columns instead of every cell`.

### R9. `match`: the whole changelist in order

`src/django_admin_kit/matching.py`: `match(rows, patterns)`, a list or tuple of row
patterns; positional check, count must equal; `ANY_ROW` holds a position; a single row
pattern means exactly one row. The failure text says "expected N rows, found M" or "row N
did not match" with the pattern and the row.

`src/django_admin_kit/pages.py`: `ChangelistPage.match`.

`tests/test_matching.py`: right order passes, wrong order fails, wrong count fails,
`ANY_ROW` at a position, `match(pattern)` with two rows fails, `match([])` on no rows
passes; the failure message names the position.
`tests/test_rows.py`: `page.match([...])` on the three products in the admin's order with
one `ANY_ROW`.

Spec: §9 heading `(done)` and the `match` examples; §9.9 `(done)`; §26 changelist
examples `# done`; §32 item 9 `(done)`; §1 bullet on row contents.

README: one entry "Reading and matching changelist rows" with `rows[0]["price"].value`,
`links`, `contains`, `match`.

Consistency: additive; `contains` is untouched.

Commit: `Match the whole changelist in order with match()`.

### After all slices

`pytest -n 4`, `ruff check`, `ruff format --check`, `mypy`, `tox -e 3.8-dj32,3.14-dj61`, and
`tox -m full` once before the pull request. Verify every mark, delete this file.

## 7. Review notes

**R1. Resolved:** the row without a change link comes from a second model, `Category`,
rather than from touching `ops_site` (decision 10).

**R2. Withdrawn:** typed numbers on a real page. Numbers are text (decision 1).

**R3. Agreed:** `display_for_field` renders a choice as its label, and the text rule
returns it as text. No `choice` rule is needed for changelists. Nothing to build here, noted
so it is not read as an omission.

**R4. Withdrawn:** the date parser. Dates are text (decision 1).

**R5. Withdrawn:** page precision of a datetime. Dates are text (decision 1).

**R6. Resolved:** `ANY` and `ANY_ROW` live in `django_admin_kit.matching`.

**R7. Withdrawn:** the three `empty_value_display` levels. An empty cell reads the text the
admin shows, whichever level set it, so no resolution is needed and no `ModelAdmin` is
reached for (decision 1).

**R8. Resolved:** cell values are text as rendered, except the boolean icon and links.
Typed dates and numbers were dropped from the package: a test of a changelist asserts what
the user reads, in the locale the browser is pinned to, and a project that wants a typed
value adds a rule through §28.3. `is_empty` went with the empty rule, since `value ==
"(none)"` says the same thing exactly. `page.count` stays a number (decision 4).
