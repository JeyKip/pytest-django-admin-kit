# Deletion confirmation contents and refused deletions: implementation plan

Spec sections 23.4 and 23.5, acceptance criteria 30 and 31 (section 32), and the last bullet of
section 1. Sections 23.1 to 23.3 are done.

## Scope

* `DeletePage.deletions`: what the admin says the deletion will remove, the object itself and
  every related object it takes with it, in the order shown.
* `DeletePage.deletion_counts`: how many objects of each model the deletion will remove, as the
  page's "Summary" counts them.
* `DeletePage.intro`: the sentence the page starts with, which asks to confirm or says why it
  cannot.
* `DeletePage.blockers`: what the page lists in place of the objects when it cannot be confirmed,
  the protected objects or the kinds of object the user may not delete.
* Section 23.5's last case, a confirmation the admin refuses when it is posted, proved by tests.
  `confirm_deleting` already reports it; no package code is expected to change for it.
* README and spec updates.

Out of scope:

* "Delete selected" on the changelist, which is changelist actions (section 33).

## What the admin renders

`admin/delete_confirmation.html`, checked in every tox env (3.2 to 6.1). Inside `#content`, in
this order, all direct children of it:

| Case | Markup |
| --- | --- |
| can be confirmed | `p` (the question), `h2` "Summary", `ul` (counts), `h2` "Objects", `ul` (the objects), `form` |
| protected | `p`, `ul` (the protected objects) |
| user may not delete some related kind | `p`, `ul` (verbose names of the kinds) |

* 4.2 added `id="deleted-objects"` to all three lists, so the id does not tell them apart and is
  missing before 4.2.
* The objects list is the only `ul` that follows an `h2` that follows another `ul`, so
  `#content > ul + h2 + ul` finds it on every version and on no other page.
* The "Summary" list is the only `ul` right after an `h2` that is right after the `p`, so
  `#content > p + h2 + ul` finds it. Each entry is `"Products: 1"`: the model's plural verbose
  name, capitalized, and the count. Django 6.1 keeps it whole when it truncates the objects list.
* The list that stands in for it on a page that cannot be confirmed is the only `ul` right after
  the `p`, so `#content > p + ul` finds it; on a page that can be confirmed, an `h2` follows the
  `p`.
* The protected list and the forbidden list are drawn alike. Only the sentence above them says
  which one the page shows, and that sentence is translated (decision 5).
* The objects list is Django's nested `unordered_list`: each entry is an `li` holding
  `"Product: Widget"`, the model's verbose name and the object's `str`, with the name linked to its
  change page when the admin site registers the model, and an `li` with related objects carries
  them in a nested `ul`. Protected objects read the same way; forbidden kinds are bare verbose
  names, such as `"product"`.
* The sentence quotes the object's name. Its quote marks changed in 4.2: `"Widget"` (question),
  `'Tools'` (refusals) before, `“Widget”` in all three after.
* Django 6.1 added `ModelAdmin.delete_confirmation_max_display`. With it set, the admin shows only
  part of a list and adds an entry "…and N more objects."; with it set to 0, it shows no list.
  The default is no limit.

## Pipeline recap

* `src/django_admin_kit/pages.py`: `DeletePage` gains `deletions`, `deletion_counts`, `intro` and
  `blockers`, each
  reading through `self._shown()`, like `can_confirm_deleting`.
* `src/django_admin_kit/rendered.py`: `text_of` collapses whitespace and reads `intro`, the flat
  `blockers` entries and the `deletion_counts` entries. `src/django_admin_kit/normalize.py`: `integer`
  reads a count however the locale groups it, as `ChangelistPage.count` does. The `deletions`
  entries need the `li`'s own text without its nested list,
  read with one `evaluate`, as `ChangelistPage._count_line` reads the paginator's own text nodes.
* `tests/project/shop/models.py` and a new migration: a model a product takes with it (C1).
* Tests: a new `tests/test_delete_contents.py`; refused confirmations in
  `tests/test_confirm_delete.py`, which already has the protected-category fixture.

## Decisions and assumptions

1. **`deletions` is a list of the entries' texts, as the user reads them:**
   `["Product: Widget", "Review: Great", "Review: Fine"]`.
   * Model instances would not do. The admin links an entry
     only when the site registers its model, and related rows of unregistered models are common
     (a many-to-many's through rows, models edited only inline), so some entries have no instance
     to read. A list of instances would leave them out and get `len` wrong.
   * Text follows section 3.4, and a list of strings needs no new type. A later release may add
     richer entries.
   * `deletions` and `deletion_counts` name everything the deletion removes, the object itself
     included, since the admin lists the object first and counts it with the rest; "dependents"
     would leave it out. `deletions` also keeps clear of a model's `objects` manager.
2. **Flattened, in the order the page shows them.** The page draws the nested list top to bottom,
   each object followed by the related objects it takes with it, and `deletions` reads the entries
   in that same order. Only the indentation is lost.
3. **`deletion_counts` is a dictionary from the label the page shows to the count**, in the order
   shown: `{"Products": 1, "Reviews": 2}`.
   * The page names each model only by its plural label, so the label is the key, as
     `IndexPage.models_for` takes the app name the index shows.
   * A model the deletion removes none of is not on the page, so it is not a key. Reading it raises
     `KeyError` listing the models the page counts, as `page.fields` does for a field the form lacks,
     so a misspelt label fails rather than reading as none; reading it as `0`, as a `Counter`
     does, would let a misspelt label pass. A test that expects none of a model writes
     `"Reviews" not in page.deletion_counts`.
   * It is `{}` on a page that cannot be confirmed, which shows no counts, and reading any model
     there raises with `Models: none.`
   * Each entry is split at its last `": "`, so a label that itself holds one stays whole.
4. **`intro` is the sentence as shown**, `""` on a page without one. Its wording depends on the
   case, on the Django version and on the language; the project decides what to assert. It is not
   called `question`, which is wrong on a refused page, or `notice`, which the spec already uses
   for the form's error banner.
5. **`blockers` is one list, not separate protected and forbidden ones.** The admin draws both
   lists the same way, so the page tells them apart only by the translated sentence above them.
   Reading the case from that sentence would tie the package to English. `blockers` reads
   whichever list the page shows, and `intro` says which case it is. Entries are in the admin's
   order; Django collects both into sets, so with several entries their order is not fixed.
   * The page shows exactly one of three things: the kinds the user may not delete, else the
     protected objects, else the deletions with their counts and the form. So `blockers` and
     `deletions` are never both non-empty: `blockers` is `[]` on a page that can be confirmed, and
     `deletions` is `[]` on one that cannot (decision 6).
   * When a deletion is blocked both ways, the admin shows only the kinds, so `blockers` reads
     those and the protected objects are not on the page. A product that protects a category is
     itself collected, so the shop's rule that a released product stays on record makes a
     category used by a released product blocked both ways: the page lists `["product"]` and not
     the product protecting it. C4 tests the blockers through categories alone.
   * A deletion blocked only by kinds, with nothing protected, would need a cascade into an
     object the user may not delete, which the test project does not have. Its list is drawn the
     same way as the other two, so it is not tested on its own.
6. **`deletions` is `[]` on a page that cannot be confirmed.** Such a page says nothing will be
   removed; what it lists there is `blockers`.
7. **A page that did not open raises `LookupError` from all four**, as every reader but
   `messages` does.
8. **Read live**, like every reader: each call reads the page as it is now, and fails once the
   browser has left it.
9. **The truncation entry of Django 6.1 is read as shown.** With `delete_confirmation_max_display`
   set, the last entry of a list is "…and N more objects."; that is what the user reads.
   Documented in the docstrings, not tested: no project setting in the suite turns it on, and
   adding one per Django version is not worth it for a project's opt-in.
10. **One addition to the test project:** `Review`, the smallest thing a product takes with it
    (C1). It is not registered with the admin, so the index and every existing test stay
    unchanged, and its entries show the unlinked form while the product's show the linked one.
    The blockers need nothing new: a category used by a product is protected, and by a released
    product blocked both ways.
11. **A confirmation for an object someone deleted after the page opened** (another user, another
    tab) is answered with a redirect to the index and a warning, so `result.success` reads `True`.
    It is left so: a user who may delete but not view is also sent to the index after a real
    deletion, so the redirect alone cannot tell the two apart, and `result.page.messages` says
    what happened.

### `Review` (test project only, C1)

| Field | Rules |
| --- | --- |
| `product` | `ForeignKey(Product, on_delete=CASCADE)`; required; not null |
| `text` | `CharField(max_length=100)`; required; not blank |

* `__str__` returns `text`; `Meta.ordering = ("pk",)` so the admin lists reviews in the order they
  were made, on every database.
* Not registered with the admin, so it is never edited there.

The migration `0002_review.py` is written in the form Django 3.2 reads, so every tox env can
apply it.

## Commit plan

### C0. Spec and plan

* `specification.md`:
  * §23.4: rewrite with texts and the real models. The example becomes
    `assert page.deletions == ["Product: Widget", "Review: Great", "Review: Fine"]`, then
    `assert "Review: Great" in page.deletions`. Add why the entries are texts (decision 1), the
    order (decision 2), and `[]` on a page that cannot be confirmed. Add `intro`, with the
    sentence as an example and a note that its wording varies with the case, the Django version
    and the language. Add `deletion_counts`, `{"Products": 1, "Reviews": 2}`, keyed by the label the
    page shows, with a model the deletion removes none of absent and raising `KeyError`.
  * §23.5: the protected-category example gains `assert page.blockers == ["Product: Widget"]`,
    and a sentence on the other case, `["product"]` for a kind the user may not delete, with
    `intro` saying which. The refused-operation example gets one sentence saying when the admin
    refuses a confirmation it offered: the object became protected, or the admin no longer lets
    the user delete it.
* This plan.
* Consistency: documents only.

### C1. Read the objects a deletion will remove

* `tests/project/shop/models.py`: `Review` as above, with a comment on why it exists and why it
  is not registered. `tests/project/shop/migrations/0002_review.py`.
* `src/django_admin_kit/pages.py`, `DeletePage.deletions`:
  * `self._shown()`, then every `li` under `#content > ul + h2 + ul`, in document order (the
    locator's `li` descendants are already in the order shown);
  * each entry's own text: the `li`'s child nodes except a nested `ul`, whitespace collapsed;
  * docstring: texts as read, in the order shown, `[]` when the page cannot be confirmed, the 6.1
    truncation entry.
* `tests/test_delete_contents.py`. Fixtures at the top: `reviewed` (the product with two reviews)
  and `deleting_product(admin_ui, superuser, product)` opening its confirmation.
  * an object nothing depends on lists only itself: `["Product: Widget"]`;
  * an object lists the related objects it takes with it, after it, in order;
  * a related object of a model the admin does not register reads the same way as one it does
    (the product's entry is a link, the reviews' are not; both read as text);
  * a page that cannot be confirmed lists nothing to remove: the protected category reads `[]`
    although the page lists the protected product;
  * a refused page raises `LookupError` with the standard "did not open" message;
  * objects held before confirming fail once the browser has left the page (`left_for`).
* Consistency: an added property, an unregistered model, and an added migration, which the suite's
  test database applies. Nothing else reads either.

### C2. Read how many objects of each model a deletion will remove

* `src/django_admin_kit/pages.py`:
  * `DeletionCounts(Dict[str, int])`, like `Fields`: a plain dict whose `__missing__` raises
    `KeyError("The page counts no model 'Reviews'. Models: 'Products'.")`, `none` when
    there are none;
  * `DeletePage.deletion_counts`: each `li` under `#content > p + h2 + ul`, split at its last
    `": "`, the label as shown and the count read with `normalize.integer`; empty when there is
    no such list. Docstring: keyed by the label the page shows, in the order shown, a model with
    no objects is absent, empty when the page cannot be confirmed, and whole even when Django 6.1
    shortens the objects list.
* Tests in `tests/test_delete_contents.py`, with the fixtures C1 added:
  * an object nothing depends on counts one of its model: `{"Products": 1}`;
  * related objects are counted by model: the reviewed product reads
    `{"Products": 1, "Reviews": 2}`;
  * a model the deletion removes none of is not counted: `"Reviews" not in` the product's counts,
    and reading it raises with the exact message listing `'Products'`;
  * a page that cannot be confirmed counts nothing: the protected category reads `{}`, and reading
    a model raises with `Models: none.`;
  * a refused page raises `LookupError`.
* Consistency: an added property.

### C3. Read the sentence the confirmation starts with

* `DeletePage.intro`: the text of `#content > p`, the first one, or `""`.
* Tests in `tests/test_delete_contents.py`, exact strings, chosen by Django version as
  `test_the_confirmation_says_what_it_is` does:
  * a page that can be confirmed asks: `Are you sure you want to delete the product “Widget”? All
    of the following related items will be deleted:` (`"Widget"` before 4.2);
  * a protected page says why: `Deleting the category “Tools” would require deleting the following
    protected related objects:` (`'Tools'` before 4.2);
  * a refused page raises `LookupError`.
* Consistency: an added property.

### C4. Read what keeps a deletion from being confirmed

* `DeletePage.blockers`: the texts of the `li` entries under `#content > p + ul`, or `[]`.
  Docstring: one list for both cases, `intro` says which, the order is the admin's, never
  non-empty next to `deletions`, and only the kinds when the deletion is blocked both ways.
* Tests in `tests/test_delete_contents.py`, with the `category`, `product` and `released`
  fixtures of `conftest.py`:
  * a protected object lists what protects it: the category used by the product reads
    `["Product: Widget"]`;
  * an object blocked both ways lists only the kind the user may not delete: the category used
    by the released product reads `["product"]`, the protected product is not on the page, its
    `intro` says so (`Deleting the category “Tools” would result in deleting related objects,
    but your account doesn't have permission to delete the following types of objects:`,
    `'Tools'` before 4.2), and `can_confirm_deleting` is false;
  * a page blocked by kinds removes nothing: that category reads `deletions == []` and
    `deletion_counts == {}`, as the protected category does in C1 and C2;
  * a page that can be confirmed has no blockers: `[]`;
  * a refused page raises `LookupError`.
* Consistency: an added property.

### C5. A confirmation the admin refuses when it is posted

Tests only, in `tests/test_confirm_delete.py`, with no package change. Each case changes the
database between opening the page and confirming:

* the category becomes protected (an unreleased product starts using it): the admin shows the confirmation
  again, so `result.success` is false, `result.page is page`, `can_confirm_deleting` is false,
  `blockers` reads `["Product: Widget"]`, and the category is still there;
* the product is released, which the shop's rule forbids deleting: the admin answers 403, so
  `result.success` is false, `result.page.denied` is true, and the product is still there;
* the product is deleted by someone else (decision 11): the admin sends the user to the index,
  so `result.success` is true, the product is gone, and
  `result.page.messages.of_level("warning")` is exactly
  `["Product with ID “<pk>” doesn’t exist. Perhaps it was deleted?"]`, as the spec's example
  asserts (with the `# noqa: RUF001` comment `test_messages.py` uses for the apostrophe).
* If any case shows that `confirm_deleting` needs a change, the fix goes in this commit.
* Consistency: tests only.

### C6. README

A short entry under deleting: reading `deletions`, `deletion_counts`, `intro` and `blockers`, and that a refused
confirmation reads as `not result.success`.

### C7. Spec marks and plan removal

`(done)` on §23.4 and §23.5's examples, section 23's title, §1's last bullet, §32 items 30 and 31.
Delete this plan.
