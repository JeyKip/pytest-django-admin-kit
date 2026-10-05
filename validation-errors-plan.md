# Validation errors: implementation plan (spec §17 to §21)

## Scope

Sections 17 to 21 of `specification.md`: submitting invalid create and edit forms, and
reading the admin's validation errors at their three levels.

What already works and only needs proving or marking:

* submitting an invalid form: `page.populate(name="")` then `page.save()` gives
  `not result.success` (§17, §18). The admin's form is `novalidate`, so the browser posts
  it whatever the `required` attributes say;
* the form rendered back with what was submitted, on `result.page` (§19, already `(done)`);
* exact, contains and complete matching (§21) are plain `list` and `dict` comparisons once
  the values below exist.

What is built:

* `page.errors`, a `ValidationErrors` on create and edit pages, with `banner`, `non_field`,
  `errors.fields` and truthiness (§20 to §21);
* `field.errors` on `FormField` (§20.3).

**Out of scope:**

* operation messages and `page.messages` (§22), though §26's example uses them;
* `result.object` (§23.1, §23.2), refused deletion results (§23.5) and the delete
  confirmation contents (§23.4);
* inline formset errors (`errorlist nonform` and errors inside inlines), deferred to 1.1.0
  with inlines;
* errors of a field the admin renders hidden. Its line is hidden, so the user never reads
  the error, and `page.fields` leaves the field out already.

## Architecture recap

* `src/django_admin_kit/pages.py`: `FormPage` (fields, actions, `submit`) and its
  `_shown()`, which every reader goes through.
* `src/django_admin_kit/fields.py`: `FormField` (one field's box, read live through its
  `check`) and `Fields` (the dict whose miss names the fields there are).
* `src/django_admin_kit/rendered.py`: `text_of`, reused for every error text.
* `tests/project/shop/admin.py`: `ProductForm`, where the rules that produce errors go.
* `tests/test_submit.py`: `PAGE_READERS`, `FIELD_READERS` and the `incomplete`,
  `rejected`, `renaming` fixtures, reused by the new tests.
* `tests/conftest.py`: `left_for`, `superuser`, `product`, `released`, `products`.

How the admin renders errors, checked in the installed templates of every tox cell:

| What | Django 3.2 to 4.1 | 4.2 to 6.0 | 6.1 |
|---|---|---|---|
| Banner | `p.errornote` in the form | same | same |
| Form-level | `ul.errorlist.nonfield` right under the banner | same | same |
| Field on its own line | `ul.errorlist` inside the line (`.form-row`) | same | inside the line's inner box |
| Field sharing a line | inside its `.fieldBox` | in a plain `div` wrapping the `.fieldBox`, before it | inside its `.fieldBox` |

The banner text is "Please correct the error below." or "Please correct the errors below."
in English on every supported version.

## Decisions

1. **Errors are read where the field's own box is.** A field's errors are the `li` items of
   the `ul.errorlist` inside its box, and, for a `.fieldBox`, of a `ul.errorlist` that is a
   direct child of the box's parent. That one rule covers all three layouts in the table:
   only the 4.2 to 6.0 wrapper `div` holds a list as a direct child, and it wraps exactly one
   field. No version check, so the public API stays version-free (§31).
2. **`ValidationErrors` is an address, like a field.** It holds two callables, one giving
   the form element and one giving `page.fields`, and reads through them each time, so it
   is live (§3.9) and fails at once on a page the browser left. `page.errors` itself runs
   the page check, as `page.fields` does.
3. **One field's errors are read from the field only: `page.fields[name].errors`.** There
   is no `page.errors[name]`, which would be a second spelling of the same read. A name the
   form does not have raises the `KeyError` that `Fields` already raises, and a field with no
   errors reads `[]`. A field can fail several rules at once, so its errors are always a
   list.
4. **`bool(page.errors)` is true when any of the three levels shows something**, so
   `assert not page.errors` holds on a page that was never submitted, and on one a project
   rendered without the banner.
5. **`banner` is the notice's text with whitespace collapsed, `""` when there is none;
   `non_field` is a list of texts, `[]` when there are none.**
6. **The test project gets its errors from `ProductForm`**, so nothing in the model or the
   migrations changes:
   * required fields left empty give "This field is required." (Django's own);
   * a SKU another product has gives "Product with this Sku already exists." (Django's own
     unique check, the realistic edit error);
   * two validators on `sku` give a field two errors at once:
     `A SKU must start with "SKU-".` and `A SKU must not contain spaces.`, both failed by
     `"bad sku"`. Every SKU the suite already saves (`SKU-1`, `SKU-Bolt` and so on) passes
     both;
   * `clean()` gives the form-level error "A featured product must be active." when
     `featured` is `True` and `is_active` is off. No existing submission sets `featured`.

   `sku` shares a line with `price`, so its errors also prove the shared-line layouts.

7. **`ValidationErrors` lives in its own module, `errors.py`**, next to `fields.py`, as
   `Row` lives in `rows.py`. `pages.py` is already near 700 lines.

## New public values

Read-only properties; nothing here is filled by a user.

| Value | Type | Empty value | Rules |
|---|---|---|---|
| `FormPage.errors` | `ValidationErrors` | falsy object | create and edit pages only; refused or left page raises `LookupError` |
| `ValidationErrors.banner` | `str` | `""` | whitespace collapsed |
| `ValidationErrors.non_field` | `list[str]` | `[]` | page order |
| `ValidationErrors.fields` | `dict[str, list[str]]` | `{}` | only fields with errors, form order |
| `FormField.errors` | `list[str]` | `[]` | a rendered-only field always `[]` |

## Commit plan

### V1: The summary notice of a rejected form

* `src/django_admin_kit/errors.py` (new): `ValidationErrors(form)` with `banner`
  (`p.errornote`, through `text_of`), `__bool__` (the banner shows, for now) and `__repr__`
  showing what it reads (pytest's `saferepr` copes if the page has gone).
* `pages.py`: `FormPage.errors`, calling `_shown()` first and passing
  `lambda: self._shown().locator("#content-main form")`.
* `tests/test_errors.py` (new):
  * a page never submitted has no errors: `not page.errors`, `banner == ""`;
  * a rejected create page with several fields missing shows
    `"Please correct the errors below."`, and one with a single field missing shows
    `"Please correct the error below."`;
  * a refused page has no errors to read (`LookupError`, the "did not open" message).
* `tests/test_submit.py`: `"errors"` added to `PAGE_READERS`.
* *Consistency:* a new property and a new module; nothing existing reads them, and the
  rejected forms the tests need already come from leaving required fields empty.

### V2: Form-level errors, apart from the notice

* `errors.py`: `non_field` (`ul.errorlist.nonfield li`), and `__bool__` widened to the
  banner or form-level errors.
* `tests/project/shop/admin.py`: `ProductForm.clean()` with the featured rule.
* `tests/test_errors.py`:
  * a page never submitted has `non_field == []`;
  * a form rejected by the featured rule lists it in `non_field`, and the banner still
    reads only the notice, `"Please correct the error below."` (§20.2: the two are not
    conflated);
  * a form rejected only for empty fields has `non_field == []`.
* *Consistency:* the form rule triggers only on a combination no existing test submits.

### V3: Field-level errors, on each field and for the whole form

* `fields.py`: `FormField.errors` per decision 1, running `check` first.
* `errors.py`: `ValidationErrors(form, fields)` takes `page.fields` as a second callable
  (`FormPage.errors` passes `lambda: self.fields`); `fields` (form order, only fields with
  errors), and `__bool__` widened to all three levels.
* `tests/project/shop/admin.py`: the two `sku` validators, set in `ProductForm.__init__`
  next to the `released_on` change and guarded the same way.
* `tests/test_errors.py`:
  * an empty required field on its own line:
    `page.fields["name"].errors == ["This field is required."]` (create, §17);
  * a field sharing a line (`sku` next to `price`) reads its own errors, not its
    neighbour's;
  * a field with two errors reads both, in order;
  * an edit page rejected for a SKU another product has (§18), using `products`;
  * `errors.fields` is the complete set for a form missing several fields (§21);
  * a field with no errors reads `[]`;
  * a rendered-only field has no errors;
  * a held `errors` object reads the page as it is now: empty before the save, filled
    after a rejected one (§3.9).
* `tests/test_submit.py`: `"errors"` added to `FIELD_READERS`.
* *Consistency:* the SKU validators accept every SKU the suite saves today, which the full
  local run confirms before the commit.

### V4: README and spec

* `README.md`: a "Finding out why a form was rejected" entry after "Submitting a form":
  `result.page.errors`, its three levels, and `field.errors`.
* `specification.md`:
  * §20: truthiness; §20.1 `""` when there is no notice;
  * `(done)` on §1's two bullets, §17 to §21, the §26 "Validation" and "Re-render" examples
    (not "Required-field population", which needs §22), and §32 items 24 to 27.
* `validation-errors-plan.md` deleted.

## Verification

`uv run pytest -n auto`, `ruff check`, `ruff format --check`, `mypy src`, then
`tox -p 6` for the eighteen cells, which cover each of the three error layouts.
