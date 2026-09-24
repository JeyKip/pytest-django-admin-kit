# Form submission plan

Implements specification section 16 (Form Submission): 16.1 Submit actions, 16.2
Post-submission navigation, 16.3 Forms with no submit actions, 16.4 The page after a
submission, and the part of 23.3/23.5 that 16.1 relies on (`confirm_deleting` and
`can_confirm_deleting` on the confirmation page).

## Scope

In scope:

* `FormPage.actions`, `has_action(name)`, and the checks `can_save`, `can_save_and_continue`,
  `can_save_and_add_another`, `can_save_as_new`, `can_delete`;
* `FormPage.submit(action)`, and `save()`, `save_and_continue()`, `save_and_add_another()`,
  `save_as_new()` and `delete()` built on it;
* `DeletePage.can_confirm_deleting` and `DeletePage.confirm_deleting()`;
* `SubmissionResult` with `success`, `redirected_to(url)`, `redirected_to_index()`,
  `redirected_to_list(model)`, `redirected_to_create(model)`, `redirected_to_edit(instance)`,
  and `page`, the page the browser shows after the submission, of the type its URL names;
* the submitted page, and every field taken from it, becoming invalid the moment it is
  submitted;
* the error for an action the page does not offer;
* a custom action in the test project, so an action the admin defines is proved end to end;
* README entries, once every slice is in, and spec marks.

Out of scope, each owned by a later section:

* `result.created`, `result.changed`, `result.object` (sections 19 and 23);
* `page.errors` on a create or edit page (sections 20 and 21) and `page.messages` on any page
  (section 22), read from the result's page after a submission;
* reading the contents of a confirmation page, `page.objects` (section 23.4);
* popups (`_popup`), inlines.

`result.page.fields` on a rejected form (section 19) needs nothing of its own: the result's
page is a fresh `CreatePage` or `EditPage`, so it is proved here and marked with the rest.

## Architecture recap

| Layer | File | What changes |
|---|---|---|
| Opening pages | `src/django_admin_kit/session.py` | nothing: `create`, `edit` and `delete` already open the pages |
| Page objects | `src/django_admin_kit/pages.py` | actions and submission on `FormPage`, confirmation on `DeletePage`, the page a URL names, the validity check on every reader |
| Fields | `src/django_admin_kit/fields.py` | `FormField` takes its page's validity and checks it on every reader |
| Validity | `src/django_admin_kit/validity.py` (new) | the small object a page and its fields share |
| Results | `src/django_admin_kit/results.py` (new) | `SubmissionResult` |
| URLs | `src/django_admin_kit/urls.py` | nothing: the shorthands call `AdminUrls.index/list/create/edit` |
| Test project | `tests/project/shop/` | `Feed` gets an admin with `save_as` and a custom action, `Product.category` protects its category |
| Tests | `tests/test_actions.py`, `tests/test_submit.py`, `tests/test_confirm_delete.py` (new) | one module per slice group |
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

For the test project's users that gives:

| User, page | `actions` |
|---|---|
| superuser, edit | `save`, `save_and_continue`, `save_and_add_another`, `delete` |
| superuser, create | `save`, `save_and_continue`, `save_and_add_another` |
| superuser, edit of a released product | `save`, `save_and_continue`, `save_and_add_another` |
| editor, edit | `save`, `save_and_continue` |
| adder, create | `save`, `save_and_add_another` |
| viewer, edit | none |
| superuser, edit of a feed | `save`, `save_and_continue`, `save_as_new`, `delete` (and `refresh` from S6) |
| superuser, create of a feed | `save`, `save_and_continue`, `save_and_add_another` |

## Decisions and assumptions

1. **Where actions are read.** The first `.submit-row` inside the page's form. `save_on_top`
   draws the same row twice, so the first one is all of them.
2. **Action names.** A submit control in the row is an action named after the `name` it posts,
   because that is what the admin's own view checks for. Django's get the spec's names:
   `_save` is `save`, `_continue` is `save_and_continue`, `_addanother` is
   `save_and_add_another`, `_saveasnew` is `save_as_new`. Any other name loses its leading
   underscore, so `_approve` is `approve`. The delete link is `delete`. The Close link is not an
   action: it submits nothing and is shown precisely when nothing can be saved, which is what
   16.3 asserts as `actions == set()`. A submit control with no `name` cannot be told apart by
   the view and is not an action.
3. **`actions` is a `set[str]`**, as the spec shows. Order is presentation and moved in 4.2.
4. **The checks are properties**, like `works`, `denied` and `editable`, each
   `self.has_action("<name>")`.
5. **`submit(action)` takes the action with no default.** It looks the action up first and,
   when the page does not offer it, raises `LookupError` before anything is clicked:
   `The page offers no action 'delete'. Actions: 'save', 'save_and_continue'.` (sorted, `none`
   when empty). `LookupError` is what a refused page raises from every reader, and what
   `Fields` and `models_for` raise for a name that is not there. The save methods are
   `return self.submit("<name>")`, so they fail the same way with the same text. Nothing was
   submitted, so the page stays valid.
6. **A submission happens in the page's own browser tab.** It clicks the control and waits
   for the navigation it causes, with Playwright's `expect_navigation`, whose value is the
   response the browser ended up on. Nothing is retyped or posted around the browser, so the
   page's scripts run as they would for a user.
7. **`success` is "the admin answered by redirecting".** Django redirects after every save,
   continue, add-another, save-as-new and delete it performs, and answers a rejected form by
   rendering it again with status 200 (or with 403 when refused). The result keeps whether the
   final response came through a redirect (`response.request.redirected_from is not None`). A
   link action (`delete`) is a plain GET, so its result is a success when the page it points to
   opened.
8. **`redirected_to(url)` requires a redirect as well as the destination.** "Save and
   continue" on an edit page and a rejected save both end on the edit URL; only the first was
   redirected there. So `redirected_to` is `redirected and page.destination == url`, and every
   shorthand is `redirected_to(self._urls.<kind>(...))`.
9. **The result reports on the submission and reaches the browser only through `page`.** It
   holds the new page, whether the navigation was redirected, and the `AdminUrls`. It has no
   `native`, `status_code` or `destination` of its own: those are the page's, read as
   `result.page.native`, `result.page.status_code` and `result.page.destination`, and nothing
   the page says is repeated on the result: validation errors and messages are read from the
   page too (sections 20 to 22). What sections 19 and 23 add to it, `created`, `changed` and
   `object`, are facts about the database that no page shows. It lives in a new `results.py`
   and is not an `AdminPage`.
10. **`result.page` has the type its URL names.** The landed path is resolved through Django's
    resolver in the site's namespace: `index` is an `IndexPage`; a registered model's
    `changelist`, `add`, `change` and `delete` views are a `ChangelistPage`, `CreatePage`,
    `EditPage` and `DeletePage` of that model; anything else is an `AdminPage`. The model is
    found by matching the URL name against each registered model's
    `<app_label>_<model_name>_` prefix, so an app label with an underscore in it is not split
    wrongly, and only public calls are used (`apps.get_models()`, `site.is_registered`). The page
    is requested at the path it landed on, so `works`, `denied` and `missing` read as they would
    for a page the test opened there itself; a submission the admin answers with the login page
    reads as `denied`. Its type is `AdminPage` to a type checker, since only the admin decides
    where a submission goes.
11. **`delete()` returns the confirmation page.** It is `submit("delete")`, whose page is
    built as a `DeletePage` requested at the link's own path, so `works`, `denied` and
    everything later read on a confirmation page read the same whether it was opened directly
    or reached from the edit page. The return type is `DeletePage`.
12. **`confirm_deleting()` and `can_confirm_deleting` are on `DeletePage`**, where the admin
    draws the button. When the page offers no confirmation, `confirm_deleting()` raises
    `LookupError`: `The page offers no way to confirm the deletion.` It returns a
    `SubmissionResult` and invalidates the confirmation page like any submission.
13. **A page is invalid once the package makes its tab load another document.** A page object
    stands for one document, and what it caches (`fields`, `actions`, and later `rows` or
    `headers`) describes that document's structure, which only a new document changes. So the
    call that navigates ends the page it was made on, whatever the outcome, and returns the
    object for the new document: a `SubmissionResult` whose `page` it is for a submission, or
    the new page itself where there is no outcome to report, as `delete()` does. In this plan
    only submissions navigate, so a changelist or an index page is never marked yet; filtering,
    sorting, searching and paging a changelist, and its bulk actions, will mark it the same way
    when they come. Interactions that load nothing, such as filling a field or ticking a row,
    leave the page valid, which holds as long as only structure is cached and values are read
    live, as `FormField.value` already is.

    `submit` marks the page right before clicking, once the action is known to be offered, so a
    page is invalid even when the admin never answers. Every reader of the page, and of every
    `FormField` taken from it, then raises `LookupError`:
    `The page was submitted, so it no longer shows what it did. Read the result's page instead.`
    That covers `native`, `status_code`, `destination`, `redirected`, `works`, `denied`,
    `missing`, `title`, `subtitle`, `fields`, `required_fields`, `optional_fields`, `actions`,
    `has_action` and the checks, `populate`, `submit` and its methods, and on a field `native`,
    `value`, `fill`, `links`, `choices`, `required`, `label` and `editable`. A field's `name`
    and `repr` stay, since they read nothing from the page and pytest prints the `repr` in a
    failure. The validity object from `validity.py` belongs to `AdminPage`, so every page type
    has one, and a page shares it with the fields it builds; its `check()` raises once it is
    marked and runs before any cached value is returned, so no cache needs clearing.
14. **`Feed` carries the admin's own action.** Its admin already exists for "Save as new", so
    the custom "Refresh" button goes on the same admin rather than on a model of its own, and
    the model's docstring grows a line saying so.
15. **A category a product uses is protected.** `Product.category` becomes `PROTECT`, so the
    suite has a confirmation page with nothing to confirm. Products, and categories no product
    uses, still delete through the ordinary confirmation, and no test deletes a category today.
16. **README waits for the whole plan.** Every slice's usage goes into the README in one
    commit after the last slice, so it describes the finished API once rather than being
    rewritten as the result grows.

## Test project changes

* `tests/project/shop/admin.py`: `admin.site.register(Feed)` becomes a `FeedAdmin` with
  `save_as = True` (S1), so the suite has one admin that offers "Save as new". `Feed` rather
  than `Product`, because on `Product` it would take "Save and add another" off every edit
  page the other tests read. `save_as_continue` keeps its default, `True`, so a copy lands on
  its own edit page.
* `tests/project/shop/templates/admin/shop/feed/submit_line.html` (new, S6): extends
  `admin/submit_line.html` and, on an edit page only (`{% if original %}`), adds
  `<input type="submit" value="Refresh" name="_refresh">` to the `submit-row` block. The admin
  looks this template up per model, so no other page changes.
* `FeedAdmin.response_change` (S6) answers `_refresh` by saving as usual and redirecting to the
  feed's history page, and defers to `super()` otherwise. A plain save goes to the changelist,
  so landing on the history page proves the project's handler ran, and it is an admin page the
  package does not model, so the result's page is a plain `AdminPage`.
* `tests/project/shop/models.py` (S8): `Product.category` becomes `on_delete=models.PROTECT`,
  so a category a product uses has a confirmation page with nothing to confirm. The migration
  is regenerated with the command in the README. No field is added; the form, its widget and
  its related-object icons are unchanged (`RelatedFieldWidgetWrapper` hides the delete icon
  only for `CASCADE`).

No field of any model gains or loses a validation rule.

## Commit plan

### Plan commit

`Spec and plan: form submission through one call per action, with a result that carries the
page the admin answered with`, carrying the spec's 16.4, the `result.page` changes to 16.2, 19,
20.3, 25 and 26, and errors and messages moving to the page in 17 and 20 to 22.

### S1. Read which actions a form offers

* `pages.py`: `_ACTIONS = {"_save": "save", "_continue": "save_and_continue", "_addanother":
  "save_and_add_another", "_saveasnew": "save_as_new"}` at the top; on `FormPage`
  `actions` (a `cached_property` of a private name-to-control map, read through `_shown()`),
  `has_action`, and the five checks.
* Test project: `FeedAdmin` with `save_as = True`; `Feed` docstring says it also stands for an
  admin that copies records. `tests/conftest.py`: a `feed` fixture
  (`Feed.objects.create(source="catalogue.csv")`).
* `tests/test_actions.py`: the table above, parametrized by user and page; `has_action` for
  an offered and an unoffered name; the five checks for the editor and for a feed's edit page;
  the viewer's edit page offers `set()` (16.3); a released product's edit page does not offer
  `delete` (5.3); a refused page raises `LookupError` from `actions`.
* Consistent: read only, nothing submits yet.

### S2. Save a form, and the page the admin answers with

* `results.py` (new): `SubmissionResult` with `success`, `redirected_to(url)` and `page`.
* `pages.py`: `FormPage.submit(action)` and `save()`; the `LookupError` of decision 5; the
  private function that builds the page a landed URL names (decision 10).
* `tests/test_submit.py`:
  * a filled create page saves: `success`, the product is in the database,
    `redirected_to(admin_ui.url.list(Product))`, and `result.page` is a `ChangelistPage` that
    works and counts one product;
  * an edit page saves a new name;
  * an empty create page is not a success and is not `redirected_to` the list; its page is a
    `CreatePage` at the create URL whose fields hold what was submitted and whose `required`
    and `choices` read as before;
  * the adder's save lands on an `IndexPage`;
  * `submit("approve")` on a page without it raises the exact message and leaves the database
    as it was; `save()` on the viewer's edit page raises `... Actions: none.`
* Consistent: `submit` knows every action S1 reads; only `save` has a method yet. The old page
  is not guarded yet, and no test reads it after submitting.

### S3. A submitted page is invalid

* `validity.py` (new): the shared object and its `check()`.
* `pages.py`: `AdminPage` creates one; every reader of decision 13 calls it; `submit` marks it
  before clicking. `fields.py`: `FormField` takes it from `FormPage.fields` and calls it in
  every reader.
* `tests/test_submit.py`: after an accepted save and after a rejected one, each reader of the
  page and of a field taken before submitting raises the exact message (parametrized by
  reader); a field's `name` and `repr` still answer; the result's page reads normally; a page
  whose action was refused by decision 5 still reads normally.
* Consistent: S2's tests read only the result, so they pass unchanged.

### S4. Save and continue, save and add another, save as new

* `pages.py`: the three methods.
* `tests/test_submit.py`: continue on an edit page is `redirected_to` its edit URL and its page
  is an `EditPage`; continue on a create page is `redirected_to` the new product's edit URL;
  add another is `redirected_to` the create URL and its page is an empty `CreatePage`; the
  editor's `save_and_add_another()` raises; a feed's `save_as_new()` after
  `populate(source="copy.csv")` leaves the original as it was, creates a second feed with the
  new source, and is `redirected_to` that feed's edit URL; a product's `save_as_new()` raises.
* Consistent: each is one line over `submit`.

### S5. Redirect shorthands

* `results.py`: `redirected_to_index()`, `redirected_to_list(model)`,
  `redirected_to_create(model)`, `redirected_to_edit(instance)`.
* `tests/test_submit.py`: each true for the save that leads there (the adder's save leads to
  the index, since the adder may not view the changelist); a rejected save on the create page
  is not `redirected_to_create(Product)` although its page is on that URL.

### S6. An action the admin defines

* Test project: the `Feed` template and `FeedAdmin.response_change` above.
* `tests/test_actions.py`: the feed's edit page row of the table gains `refresh`.
* `tests/test_submit.py`: the feed's create page does not offer `refresh`;
  `submit("refresh")` saves what was populated, is `redirected_to` the feed's history page, and
  its page is a plain `AdminPage` that works.
* `test_index.py` is unaffected (the model list is unchanged).

### S7. Delete from the edit page

* `pages.py`: `FormPage.delete()` over `submit("delete")`, returning the result's page, a
  `DeletePage`.
* `tests/test_confirm_delete.py`: from the superuser's edit page, `delete()` opens the
  confirmation (`works`, destination is `admin_ui.url.delete(product)`), and the edit page is
  invalid afterwards; the editor's `delete()` raises; a create page's `delete()` raises.
* Consistent: nothing confirms yet; the confirmation page is read like one opened directly.

### S8. Confirm a deletion

* `tests/project/shop/models.py` and the regenerated migration: `PROTECT`.
* `pages.py`: `DeletePage.can_confirm_deleting`, `DeletePage.confirm_deleting()`.
* `tests/test_confirm_delete.py`: a superuser confirms, the result is a success,
  `redirected_to_list(Product)`, its page is a `ChangelistPage`, the product is gone, and the
  confirmation page is invalid; confirming the page `delete()` reached works the same; a
  category a product uses cannot be confirmed and `confirm_deleting()` raises the exact
  message, deleting nothing; a refused confirmation page raises `LookupError` from
  `can_confirm_deleting`.

### S9. README

* `README.md`: "Knowing what a form lets the user do" (actions and checks), "Submitting a
  form" (the save methods, a custom action through `submit`, `success`, `redirected_to` and the
  shorthands, `result.page`, and the submitted page becoming invalid), and "Deleting" (the two
  steps and a confirmation that cannot be made). Examples use the test project's real models,
  one item per line.

### S10. Spec marks and plan removal

* `specification.md`: `(done)` on 16, 16.1, 16.2, 16.3, 16.4, 5.3, the §1 bullet, §32 items
  20 to 23; §19's sentence on the re-rendered form being the result's page; the parts of 23.3
  and 23.5 this delivers.
* Delete `form-submission-plan.md`.

## Review notes

None open.
