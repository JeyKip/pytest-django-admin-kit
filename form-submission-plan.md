# Form submission plan

Implements specification section 3.9 (Live reads) and section 16 (Form Submission): 16.1
Submit actions, 16.2 Post-submission navigation, 16.3 Forms with no submit actions, 16.4 The
page after a submission, and the part of 23.3/23.5 that 16.1 relies on (`confirm_deleting` and
`can_confirm_deleting` on the confirmation page).

## Scope

In scope:

* no value read from the page or the database is kept: every read is live (3.9);
* a page object stays usable while the browser shows its path and its kind, and fails at once
  otherwise, as does anything taken from it (3.9, 16.4);
* `FormPage.actions`, `has_action(name)`, and the checks `can_save`, `can_save_and_continue`,
  `can_save_and_add_another`, `can_save_as_new`, `can_delete`;
* `FormPage.submit(action)`, and `save()`, `save_and_continue()`, `save_and_add_another()`,
  `save_as_new()` and `delete()` built on it;
* `DeletePage.can_confirm_deleting` and `DeletePage.confirm_deleting()`;
* `SubmissionResult` with `success`, `redirected_to(url)`, `redirected_to_index()`,
  `redirected_to_list(model)`, `redirected_to_create(model)`, `redirected_to_edit(instance)`,
  and `page`: the submitted page itself when the browser stayed on it, otherwise a new page of
  the type its URL names;
* the error for an action the page does not offer;
* a custom action in the test project, so an action the admin defines is proved end to end;
* README entries, once every slice is in, and spec marks.

Out of scope, each owned by a later section:

* `result.created`, `result.changed`, `result.object` (sections 19 and 23);
* `page.errors` on a create or edit page (sections 20 and 21) and `page.messages` on any page
  (section 22);
* reading the contents of a confirmation page, `page.objects` (section 23.4);
* changelist filtering, sorting, searching, paging and bulk actions, which will follow the
  same rules without anything new;
* popups (`_popup`), inlines.

`result.page.fields` on a rejected form (section 19) needs nothing of its own: the result's
page is the submitted form, read live, so it is proved here and marked with the rest.

## Architecture recap

| Layer | File | What changes |
|---|---|---|
| Opening pages | `src/django_admin_kit/session.py` | nothing: `create`, `edit` and `delete` already open the pages |
| Page objects | `src/django_admin_kit/pages.py` | no caching; the page check; actions and submission on `FormPage`; confirmation on `DeletePage`; the page a URL names |
| Fields | `src/django_admin_kit/fields.py` | no caching; `FormField` takes its page's check |
| Rows | `src/django_admin_kit/rows.py` | no caching; `Row` and `Cell` take their page's check |
| Rendered values | `src/django_admin_kit/rendered.py` | no caching |
| Results | `src/django_admin_kit/results.py` (new) | `SubmissionResult` |
| URLs | `src/django_admin_kit/urls.py` | nothing: the shorthands call `AdminUrls.index/list/create/edit` |
| Test project | `tests/project/shop/` | `Feed` gets an admin with `save_as` and a custom action, `Product.category` protects its category |
| Tests | `tests/test_live.py`, `tests/test_actions.py`, `tests/test_submit.py`, `tests/test_confirm_delete.py` (new) | one module per slice group |
| Docs | `README.md`, `specification.md` | README once every slice is in, marks at the end |

Reused as they are: `AdminPage._shown()` (a refused page raises `LookupError` from every reader,
so `actions`, the checks and every submitting method inherit that), `AdminPage.destination`
(path only, query dropped), `AdminUrls` for the shorthands, `_token`/`_text` helpers in
`pages.py`, and the waiting pattern of `AdminSession._login_with_form`.

## What Django renders

Read from `submit_line.html` and `admin_modify.submit_row` on Django 3.2 to 6.1 (the markup
moved the delete link from before to after the save buttons in 4.2, and added `role="button"`
in 6.0; neither changes what is read below):

| Control | Markup | Shown when |
|---|---|---|
| Save | `input[type=submit][name=_save]` | the user may change (edit) or add (create) |
| Save and continue editing | `input[type=submit][name=_continue]` | as Save, and the user may view |
| Save and add another | `input[type=submit][name=_addanother]` | as Save, and the user may add |
| Save as new | `input[type=submit][name=_saveasnew]` | `save_as = True`, edit page; the user may change (3.2 to 4.1) or add (4.2 on); replaces Save and add another |
| Delete | `a.deletelink` | edit page, and the user may delete this object |
| Close | `a.closelink` | whenever Save is not shown |

The confirmation page renders `input[type=submit]` inside `#content form` only when nothing is
protected and no permission is lacking; otherwise it lists what stands in the way and has no
form.

Every admin template names its kind in the `body` class, identically from 3.2 to 6.1:
`change-list`, `change-form`, `delete-confirmation` (plus `delete-selected-confirmation` for
the bulk one), `dashboard`, `login`, next to `app-<label> model-<name>`.

For the test project's users that gives:

| User, page | `actions` |
|---|---|
| superuser, edit | `save`, `save_and_continue`, `save_and_add_another`, `delete` |
| superuser, create | `save`, `save_and_continue`, `save_and_add_another` |
| superuser, edit of a released product | `save`, `save_and_continue`, `save_and_add_another` |
| editor, edit | `save`, `save_and_continue` |
| adder, create | `save`, `save_and_add_another` |
| viewer, edit | none |
| superuser, edit of a feed | `save`, `save_and_continue`, `save_as_new`, `delete` (and `refresh` from S7) |
| superuser, create of a feed | `save`, `save_and_continue`, `save_and_add_another` |

## Decisions and assumptions

1. **Nothing read is kept.** Every `cached_property` that holds something read from the
   browser or the database becomes a plain property: `IndexPage._app_list`,
   `ChangelistPage.rows`, `_header_cells`, `_count_line`, `FormPage.fields`,
   `FormField.required`, `label`, `editable`, `choices`, `RenderedValue.text`, `value`,
   `links`, `Row.object`, `Row._cells`. `FormField._label` and `_rendered` hold locators, which
   are queries rather than results, and become plain properties too so the modules have one
   rule. A read that needs a value twice within one call reads it once into a local.
2. **Held objects are addresses.** A `FormField` is its name, a `Row` its position, a `Cell`
   its column within its row, each read when used, like a Playwright locator. `page.rows` and
   `page.fields` return a new list and dictionary on every read. A `Row` is given the column
   list when it is built: the same path and kind means the same `list_display` in practice.
3. **Where Playwright has an answer, the package gives the same one.** Reading an address that
   finds nothing waits for the timeout and fails as Playwright does; navigation through
   `native` is the test's to wait for; wrappers compare by identity. None of these gets code
   of its own (see "Known problems").
4. **A page object stands for its path and its kind.** Its kind is the admin's `body` class for
   its page type: `change-list` for `ChangelistPage`, `change-form` for `CreatePage` and
   `EditPage`, `delete-confirmation` for `DeletePage`, `dashboard` for `IndexPage`; a plain
   `AdminPage` has no kind and is held to its path alone. Every reader of a page, and of a
   `FormField`, `Row` or `Cell` taken from it, first runs the page's check: the tab's current
   path (read from `tab.url`, which costs no round trip) and, for a page with a kind, its
   `body` class must match. Otherwise it raises `LookupError` at once:
   `The browser no longer shows this page; it is at /admin/shop/product/. Read the page it shows now, such as a submission's result.page.`
   The page hands the check to the objects it builds. `native`, a field's `name`, a row's
   `index`, a cell's `column` and every `repr` read nothing from the page and are exempt; a
   native handle is Playwright's own object and behaves as Playwright decides.
5. **Where actions are read.** The first `.submit-row` inside the page's form. `save_on_top`
   draws the same row twice, so the first one is all of them.
6. **Action names.** A submit control in the row is an action named after the `name` it posts,
   because that is what the admin's own view checks for. Django's get the spec's names:
   `_save` is `save`, `_continue` is `save_and_continue`, `_addanother` is
   `save_and_add_another`, `_saveasnew` is `save_as_new`. Any other name loses its leading
   underscore, so `_approve` is `approve`. The delete link is `delete`. The Close link is not an
   action: it submits nothing and is shown precisely when nothing can be saved, which is what
   16.3 asserts as `actions == set()`. A submit control with no `name` cannot be told apart by
   the view and is not an action.
7. **`actions` is a `set[str]`**, as the spec shows. Order is presentation and moved in 4.2.
8. **The checks are properties**, like `works`, `denied` and `editable`, each
   `self.has_action("<name>")`.
9. **`submit(action)` takes the action with no default.** It looks the action up first and,
   when the page does not offer it, raises `LookupError` before anything is clicked:
   `The page offers no action 'delete'. Actions: 'save', 'save_and_continue'.` (sorted, `none`
   when empty). `LookupError` is what a refused page raises from every reader, and what
   `Fields` and `models_for` raise for a name that is not there. The save methods are
   `return self.submit("<name>")`, so they fail the same way with the same text. Nothing was
   submitted, so the page is as it was.
10. **A submission happens in the page's own browser tab.** It clicks the control and waits
    for the navigation it causes, with Playwright's `expect_navigation`, whose value is the
    response the browser ended up on. Nothing is retyped or posted around the browser, so the
    page's scripts run as they would for a user.
11. **`success` is "the admin answered by redirecting".** Django redirects after every save,
    continue, add-another, save-as-new and delete it performs, and answers a rejected form by
    rendering it again with status 200 (or with 403 when refused). The result keeps whether the
    final response came through a redirect (`response.request.redirected_from is not None`). A
    link action (`delete`) is a plain GET, so its result is a success when the page it points
    to opened.
12. **`redirected_to(url)` requires a redirect as well as the destination.** "Save and
    continue" on an edit page and a rejected save both end on the edit URL; only the first was
    redirected there. So `redirected_to` is `redirected and page.destination == url`, and every
    shorthand is `redirected_to(self._urls.<kind>(...))`.
13. **The result reports on the submission and reaches the browser only through `page`.** It
    holds the page, whether the navigation was redirected, and the `AdminUrls`. It has no
    `native`, `status_code` or `destination` of its own, and nothing the page says is repeated
    on it: validation errors and messages are read from the page (sections 20 to 22). What
    sections 19 and 23 add to it, `created`, `changed` and `object`, are facts about the
    database that no page shows. It lives in a new `results.py` and is not an `AdminPage`.
14. **`result.page` is the submitted page when the browser stayed on it.** After the
    navigation, the page's own check (decision 4) decides: if the browser still shows the
    submitted page's path and kind, the result's page is that same object, and it records the
    new response's status and the path it was asked for, so `status_code` and `works` describe
    the document it now reads. Otherwise the result's page is a new object of the type the
    landed URL names: the path is resolved through Django's resolver in the site's namespace;
    `index` is an `IndexPage`; a registered model's `changelist`, `add`, `change` and `delete`
    views are a `ChangelistPage`, `CreatePage`, `EditPage` and `DeletePage` of that model;
    anything else is an `AdminPage`. The model is found by matching the URL name against each
    registered model's `<app_label>_<model_name>_` prefix, so an app label with an underscore
    in it is not split wrongly, and only public calls are used (`apps.get_models()`,
    `site.is_registered`). A new page is requested at the path it landed on, so a submission
    the admin answers with the login page reads as `denied`. Its type is `AdminPage` to a type
    checker, since only the admin decides where a submission goes.
15. **`delete()` returns the confirmation page.** It is `submit("delete")`, whose page is built
    as a `DeletePage` requested at the link's own path, so `works`, `denied` and everything
    later read on a confirmation page read the same whether it was opened directly or reached
    from the edit page. The return type is `DeletePage`, and the edit page it came from fails
    its check afterwards, since the browser left it.
16. **`confirm_deleting()` and `can_confirm_deleting` are on `DeletePage`**, where the admin
    draws the button. When the page offers no confirmation, `confirm_deleting()` raises
    `LookupError`: `The page offers no way to confirm the deletion.` It returns a
    `SubmissionResult`; the admin redirects after a deletion, so the confirmation page fails
    its check afterwards like any page the browser left.
17. **`Feed` carries the admin's own action.** Its admin already exists for "Save as new", so
    the custom "Refresh" button goes on the same admin rather than on a model of its own, and
    the model's docstring grows a line saying so.
18. **A category a product uses is protected.** `Product.category` becomes `PROTECT`, so the
    suite has a confirmation page with nothing to confirm. Products, and categories no product
    uses, still delete through the ordinary confirmation, and no test deletes a category today.
19. **README waits for the whole plan.** Every slice's usage goes into the README in one
    commit after the last slice, so it describes the finished API once.

## Known problems and what is done about them

Reading live has consequences. Where plain Playwright has the same one, the package behaves
the same way and documents it; it adds code only for what exists because the package itself
moves the browser between pages.

| Problem | Same in plain Playwright? | What is done |
|---|---|---|
| A held object whose page the browser has left (after a save that redirected, a `delete()`, a native navigation) would read another page, or wait for the timeout against it | no: Playwright has no object standing for "an edit page" | the page check (decision 4) raises at once, saying where the browser is |
| Reading an address that finds nothing on the same page, such as `rows[4]` after a filter left two rows | yes: `nth(4)` waits for the timeout | nothing; documented in 3.9 |
| A held row reads a different record after a filter or a sort | yes: `nth()` is positional | nothing; documented in 3.9 and on `Row.index` |
| `page.rows` and `page.fields` hold the rows and fields present when read | yes: `locator.all()` does the same | nothing; documented in 3.9 |
| A row maps cells to the column list it was built with | no, but only a project whose `list_display` changes with the query string could notice | documented as an assumption on `Row` |
| A read right after a navigation started through `native` may see the old document | yes | nothing; the package's own actions wait; documented in 3.9 |
| Wrappers compare by identity, so two reads of one field are not `==` | yes: locators compare by identity | nothing; documented in 3.9 |
| `row.object` asks the database each time, so it follows changes and can raise `DoesNotExist` | not applicable | nothing; that is the live answer; documented on `Row.object` and in 3.9 |
| `status_code` and `works` cannot be read from the page | not applicable | the package's navigating methods record them (decision 14); a native navigation is not seen, documented in 3.9 |
| `populate` fills the fields shown when it starts, so one a script adds meanwhile is not filled | not applicable | nothing; documented in 14.1 |
| A row match compares cells and reports them in two reads, which could differ if a script changes the page in between | yes: `expect` reports the value of its last poll | nothing |
| Every read is a round trip | yes | accepted |

## Test project changes

* `tests/project/shop/admin.py`: `admin.site.register(Feed)` becomes a `FeedAdmin` with
  `save_as = True` (S2), so the suite has one admin that offers "Save as new". `Feed` rather
  than `Product`, because on `Product` it would take "Save and add another" off every edit
  page the other tests read. `save_as_continue` keeps its default, `True`, so a copy lands on
  its own edit page.
* `tests/project/shop/templates/admin/shop/feed/submit_line.html` (new, S7): extends
  `admin/submit_line.html` and, on an edit page only (`{% if original %}`), adds
  `<input type="submit" value="Refresh" name="_refresh">` to the `submit-row` block. The admin
  looks this template up per model, so no other page changes.
* `FeedAdmin.response_change` (S7) answers `_refresh` by saving as usual and redirecting to the
  feed's history page, and defers to `super()` otherwise. A plain save goes to the changelist,
  so landing on the history page proves the project's handler ran, and it is an admin page the
  package does not model, so the result's page is a plain `AdminPage`.
* `tests/project/shop/models.py` (S9): `Product.category` becomes `on_delete=models.PROTECT`,
  so a category a product uses has a confirmation page with nothing to confirm. The migration
  is regenerated with the command in the README. No field is added; the form, its widget and
  its related-object icons are unchanged (`RelatedFieldWidgetWrapper` hides the delete icon
  only for `CASCADE`).

No field of any model gains or loses a validation rule.

## Commit plan

### Plan commit

`Spec and plan: read every value live and hold a page to its path and kind`, carrying the
spec's 3.9, the rewritten 16.4, and the notes in 14.1 and 19.

### S1. Read every value live

* `pages.py`, `fields.py`, `rows.py`, `rendered.py`: every `cached_property` of decision 1
  becomes a property; `ChangelistPage.count` and `summary` each read the count line once;
  docstrings on `Row.index` (a position) and `Row.object` (asked of the database each time).
* `tests/test_live.py`:
  * a cell whose text a script changes in place (through `native.evaluate`) reads the new text;
  * a row held while a script removes the first row reads the record now at its position;
  * a field a script removes from the form is gone from `page.fields` read again, and a
    `Fields` read before still names it;
  * `row.object` read after the product is renamed in the database has the new name.
* Consistent: the whole suite passes unchanged, which shows nothing relied on a kept value.

### S2. Read which actions a form offers

* `pages.py`: `_ACTIONS = {"_save": "save", "_continue": "save_and_continue", "_addanother":
  "save_and_add_another", "_saveasnew": "save_as_new"}` at the top; on `FormPage` `actions`
  (read through `_shown()`), `has_action`, and the five checks.
* Test project: `FeedAdmin` with `save_as = True`; `Feed` docstring says it also stands for an
  admin that copies records. `tests/conftest.py`: a `feed` fixture
  (`Feed.objects.create(source="catalogue.csv")`).
* `tests/test_actions.py`: the table above, parametrized by user and page; `has_action` for
  an offered and an unoffered name; the five checks for the editor and for a feed's edit page;
  the viewer's edit page offers `set()` (16.3); a released product's edit page does not offer
  `delete` (5.3); a refused page raises `LookupError` from `actions`.
* Consistent: read only, nothing submits yet.

### S3. Save a form, and the page the admin answers with

* `results.py` (new): `SubmissionResult` with `success`, `redirected_to(url)` and `page`.
* `pages.py`: `FormPage.submit(action)` and `save()`; the `LookupError` of decision 9; the
  path-and-kind comparison and the page a landed URL names (decision 14); recording the new
  status and requested path on a page the browser stayed on.
* `tests/test_submit.py`:
  * a filled create page saves: `success`, the product is in the database,
    `redirected_to(admin_ui.url.list(Product))`, and `result.page` is a new `ChangelistPage`
    that works and counts one product;
  * an edit page saves a new name;
  * an empty create page is not a success and is not `redirected_to` the list; its page is the
    submitted page itself (`result.page is page`), it works, and its fields hold what was
    submitted;
  * the adder's save lands on an `IndexPage`;
  * `submit("approve")` on a page without it raises the exact message and leaves the database
    as it was; `save()` on the viewer's edit page raises `... Actions: none.`
* Consistent: the page check is not enforced yet, and no test reads a page the browser left.

### S4. A page the browser has left fails at once

* `pages.py`: the check of decision 4 at the start of every page reader; the page hands it to
  the `FormField`, `Row` and `Cell` objects it builds. `fields.py`, `rows.py`: each reader runs
  the check it was given.
* `tests/test_submit.py`: after a save that redirected, each reader of the page and of a field
  taken before the save raises the exact message at once (parametrized by reader); `native`,
  a field's `name` and `repr` still answer.
* `tests/test_live.py`: a changelist left through `page.native.goto(...)` raises from `rows`,
  `count` and a held row; the same path showing another kind of page (a Playwright route that
  answers the changelist URL with the index markup, then a native reload) raises too.
* Consistent: S3's tests read only pages the browser shows, so they pass unchanged.

### S5. Save and continue, save and add another, save as new

* `pages.py`: the three methods.
* `tests/test_submit.py`: continue on an edit page is `redirected_to` its edit URL and its page
  is the same object; continue on a create page is `redirected_to` the new product's edit URL
  and its page is a new `EditPage`, the create page failing its check; add another is
  `redirected_to` the create URL and its page is the same object, now empty; the editor's
  `save_and_add_another()` raises; a feed's `save_as_new()` after `populate(source="copy.csv")`
  leaves the original as it was, creates a second feed with the new source, and is
  `redirected_to` that feed's edit URL; a product's `save_as_new()` raises.
* Consistent: each is one line over `submit`.

### S6. Redirect shorthands

* `results.py`: `redirected_to_index()`, `redirected_to_list(model)`,
  `redirected_to_create(model)`, `redirected_to_edit(instance)`.
* `tests/test_submit.py`: each true for the save that leads there (the adder's save leads to
  the index, since the adder may not view the changelist); a rejected save on the create page
  is not `redirected_to_create(Product)` although its page is on that URL.

### S7. An action the admin defines

* Test project: the `Feed` template and `FeedAdmin.response_change` above.
* `tests/test_actions.py`: the feed's edit page row of the table gains `refresh`.
* `tests/test_submit.py`: the feed's create page does not offer `refresh`;
  `submit("refresh")` saves what was populated, is `redirected_to` the feed's history page, and
  its page is a plain `AdminPage` that works.
* `test_index.py` is unaffected (the model list is unchanged).

### S8. Delete from the edit page

* `pages.py`: `FormPage.delete()` over `submit("delete")`, returning a `DeletePage`.
* `tests/test_confirm_delete.py`: from the superuser's edit page, `delete()` opens the
  confirmation (`works`, destination is `admin_ui.url.delete(product)`), and the edit page
  fails its check afterwards; the editor's `delete()` raises; a create page's `delete()`
  raises.
* Consistent: nothing confirms yet; the confirmation page is read like one opened directly.

### S9. Confirm a deletion

* `tests/project/shop/models.py` and the regenerated migration: `PROTECT`.
* `pages.py`: `DeletePage.can_confirm_deleting`, `DeletePage.confirm_deleting()`.
* `tests/test_confirm_delete.py`: a superuser confirms, the result is a success,
  `redirected_to_list(Product)`, its page is a `ChangelistPage`, the product is gone, and the
  confirmation page fails its check; confirming the page `delete()` reached works the same; a
  category a product uses cannot be confirmed and `confirm_deleting()` raises the exact
  message, deleting nothing; a refused confirmation page raises `LookupError` from
  `can_confirm_deleting`.

### S10. README

* `README.md`: "Reading is live" (addresses, and a page the browser left failing at once),
  "Knowing what a form lets the user do" (actions and checks), "Submitting a form" (the save
  methods, a custom action through `submit`, `success`, `redirected_to` and the shorthands,
  `result.page` being the same page or a new one), and "Deleting" (the two steps and a
  confirmation that cannot be made). Examples use the test project's real models, one item per
  line.

### S11. Spec marks and plan removal

* `specification.md`: `(done)` on 3.9, 16, 16.1, 16.2, 16.3, 16.4, 5.3, the §1 bullet, §32
  items 20 to 23; the 14.1 note; §19's sentence on the re-rendered form being the result's
  page; the parts of 23.3 and 23.5 this delivers.
* Delete `form-submission-plan.md`.

## Review notes

None open.
