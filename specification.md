# Django Admin Testing Package — 1.0.0 Specification

# 1. Purpose

The package provides a pytest-oriented API for testing Django Admin behavior.

It should allow developers to verify:

* authentication and access with different users (done);
* effective admin permissions, including constraints imposed by the admin configuration itself;
* availability and basic operation of admin pages;
* the set of models the admin exposes;
* changelist columns, record counts, and row contents;
* create and edit form fields, including their labels, initial values, and choices;
* editable and rendered-only field values;
* requiredness of create and edit form fields;
* automatic population of form fields;
* submit actions and where the admin navigates after an operation;
* validation errors displayed by Django Admin;
* what a form renders back after an invalid submission;
* messages displayed after an operation;
* the contents of a deletion confirmation.

The package should emphasize readable tests using normal Python `assert` statements rather than
custom assertion methods wherever practical.

Tests exercise the admin as a real browser renders it. See section 2.2.

The minimum supported Django version is **Django 3.2**, and the minimum supported Python
version is **Python 3.8**.

---

# 2. Scope of 1.0.0

## 2.1 Covered in 1.0.0

1.0.0 covers standard Django Admin functionality for simple models.

Supported relationships and field behavior should be limited to fields that can be represented
as ordinary scalar form values.

Foreign keys may be supported where they behave as a normal single-value form field, but
automatic traversal or creation of related object graphs is not required for 1.0.0.

---

## 2.2 Driving model (done)

The package drives the admin **as a real browser renders it**, against a live server.

Consequences, all deliberate:

* what a test observes is what a user would see, with the page's own scripts having run;
* the response status of a page is part of the public contract, not an optional extra;
* the package may use the full capability of the browser layer it is built on, rather than
  restricting itself to a portable subset.

This has a price, and adopters should price it in rather than discover it: tests need browser
binaries and a live server, and are slower than tests that exercise the admin through the
request cycle alone. The package offers no faster path and no way to opt out.

The reach of this decision stops at what Django Admin itself renders. Everything a project
renders on top of the admin is reached differently; see section 3.6.

---

## 2.3 Deferred

Relational and compound admin forms, changelist interaction, and advanced field representations
are deferred.

The ordered roadmap is defined in section 33.

---

# 3. Design Principles

## 3.1 Pytest-style assertions

Tests should look like ordinary pytest tests.

Preferred:

```python
assert page.works
assert page.has_field("first_name")
assert page.field("email").required
assert page.contains([...])
```

Avoid making the primary interface:

```python
page.assertFieldExists(...)
page.assertPageWorks(...)
```

Where failure diagnostics require more context, objects returned by the library should implement
useful comparison behavior and pytest assertion introspection where possible.

---

## 3.2 Explicit over implicit

Tests should clearly express:

* which user is being used;
* which model is being tested;
* which admin page is being tested;
* which values are expected;
* which values should be generated automatically.

Automatic behavior should remain predictable and inspectable.

---

## 3.3 Stable public abstraction

Tests should interact with package-level abstractions rather than depending directly on Django
Admin internals.

Typical concepts exposed by the package:

```python
admin_ui                   # done
admin_ui.login(...)        # done
admin_ui.permissions(...)
admin_ui.index()           # done
admin_ui.list(...)
admin_ui.create(...)
admin_ui.edit(...)
admin_ui.delete(...)
```

Page objects should expose normalized information such as fields, errors, headers, rows,
messages, and status.

---

## 3.4 Normalized values

The package compares **meaning**, not markup.

A value read from an admin page is normalized before a test ever sees it:

* a boolean cell normalizes to a boolean, however the admin chooses to draw it;
* an absent or blank value normalizes to the empty value;
* a value the admin renders as a link normalizes to its text, with the target available
  separately;
* dates, times, and numbers normalize through the formats and time zone the project has
  configured;
* text normalizes from the document's own content, never from its rendered presentation, so
  styling such as letter-casing never changes a value.

A test must never need to know how a value was rendered:

```python
assert page.row(1)["Active"] is True
assert page.row(1)["Middle name"] == ""
```

Tests must not hardcode a rendering format.

Every normalization rule is a package setting with a documented default, and every one of them
can be replaced by the project. Nothing about normalization is fixed inside the package. See
section 28.3.

---

## 3.5 Addressing by name

The package uses one coordinate vocabulary everywhere it applies:

* rows are addressed by 1-based position;
* cells are addressed by column;
* fields are addressed by name.

```python
page.row(1)
page.row(1)["Email"]
page.field("email")
```

Positional cell access remains available where a tuple comparison is the clearer expression.

---

## 3.6 Native access

A package can only generalize what Django Admin itself renders. Every real project adds custom
admin views, overridden templates, custom widgets, and third-party admin applications, and a
test must be able to reach those.

The API therefore has two tiers, and one rule decides which applies:

> If Django Admin renders it, the package normalizes it.
> If your project renders it, you take a native handle.

Both tiers appear in the same test, without leaving the package:

```python
page = admin_ui.edit(product)

assert page.field("name").required            # standard field, package vocabulary
page.field("colour_picker").native.click()    # the project's own widget, native handle
```

Reaching for a native handle is **expected and supported**, not a failure or a last resort. A
project keeps the package's login, navigation, URL resolution and normalization, and drops to
the browser only for the part the package cannot know about.

Native handles are available at every level of the object model:

```python
admin_ui.native                        # done
page.native                            # done
page.field("name").native
page.row(1).native
page.row(1).cell("Email").native
```

They are the underlying browser library's own objects. The package does not wrap, restrict, or
re-export them, so their type is part of this package's public surface and changes to it are
breaking changes.

---

## 3.7 Reusable page contracts

Projects test many admin pages that differ only in their model and their expected shape.

Expressing a page's expected shape once and applying it to many models must be natural.

The package must not prescribe a class hierarchy, and must not require a project to subclass a
package-provided test case in order to reuse expectations.

---

## 3.8 Project-level adjustability

The package ships nothing project-specific.

Every project-specific behavior enters through a documented extension point rather than through
a fork, a subclass requirement, or a special case inside the package.

See section 28.

---

# 4. Authentication (done)

The package must support using any Django user object.

At minimum:

```python
admin_ui.login(admin_user)
admin_ui.login(staff_user)
admin_ui.login(arbitrary_user)
```

The package must not assume that:

* the user model uses `username`;
* the default Django `User` model is installed;
* only superusers can access Admin;
* the caller knows the user's password.

An arbitrary custom user model must therefore be usable as long as the Django project itself
supports it.

Passwords are stored irreversibly, so `login(user)` must never require one. A user with no
usable password at all must still be able to log in.

Where a test's own subject is the login page, an explicit password may be supplied:

```python
admin_ui.login(user, password="secret")
```

This drives the rendered login form, typing the value the user model identifies users by, such
as an email address on a model without a `username`. It is an opt-in for testing the login page,
never a requirement for logging in.

Example:

```python
admin_ui.login(user)

page = admin_ui.index()

assert page.works
```

The test author must also be able to switch users during a test:

```python
admin_ui.login(user_a)
...
admin_ui.login(user_b)
...
```

Logout should also be available:

```python
admin_ui.logout()
```

---

# 5. Permission Testing

## 5.1 Model permissions

The package must expose the effective Django Admin permissions of a user for a model.

The four standard permissions are:

* view;
* add;
* change;
* delete.

A model may declare permissions beyond these, and may narrow or remove the standard ones; see
section 5.2.

Example API:

```python
permissions = admin_ui.permissions(Product)

assert permissions.view
assert permissions.add
assert permissions.change
assert not permissions.delete
```

A compact form should also be possible:

```python
assert admin_ui.permissions(Product) == {
    "view": True,
    "add": True,
    "change": True,
    "delete": False,
}
```

Permission checks must represent the permissions applicable to the currently logged-in user.

The API should also support permission testing without requiring the corresponding page to be
opened.

---

## 5.2 Custom permissions

The four standard permissions are not a closed set.

A model may declare permissions of its own, and may narrow or remove the standard ones. An admin
may additionally gate one of its own operations behind a permission that is neither standard nor
declared by the model.

The package must therefore address permissions by name, not only by the four fixed attributes:

```python
permissions = admin_ui.permissions(Product)

assert permissions["publish"]
assert not permissions["archive"]
```

Presence of a permission is distinct from its value:

```python
assert permissions.has("publish")
```

The complete effective set must be readable:

```python
assert permissions.all == {
    "view": True,
    "add": True,
    "change": True,
    "delete": False,
    "publish": True,
}
```

Equality compares the complete effective set. A model that declares no custom permissions and
narrows none of the standard ones therefore reports exactly the four of section 5.1, and the
compact comparison there stays correct.

---

## 5.3 Effective permissions

Reported permissions must be **effective** permissions.

A user's assigned permissions are not the whole answer: an admin registration may impose further
constraints of its own, and may grant or withhold an operation independently of the permission
system.

The package must report what the admin will actually allow.

---

## 5.4 Per-object permissions

Permissions must also be inspectable for a specific object:

```python
assert admin_ui.permissions(product).change
assert not admin_ui.permissions(product).delete
assert admin_ui.permissions(product)["publish"]
```

The model form and the object form share one public representation, custom permissions included.

Two independent sources can make an object's permissions differ from its model's: the admin can
decide per object, and an authentication backend can answer per object. The package reports the
combined effective result, and never requires a test to say which source produced it.

Django's default authentication backend does not answer per-object questions. A project whose
per-object rules live in its admin needs nothing further; a project that expects the permission
system itself to answer per object must be running a backend that supports it. The package must
behave the same way in both cases.

---

## 5.5 Observable consequences

A page the current user may not open must not report itself as working, and must say why:

```python
page = admin_ui.edit(product)

assert not page.works
assert page.denied
```

---

# 6. Admin Page Availability

The package must provide abstractions for the admin index and for these four standard model
admin operations:

```python
admin_ui.index()           # done

admin_ui.list(Model)
admin_ui.create(Model)
admin_ui.edit(instance)
admin_ui.delete(instance)
```

Each returned page must make it easy to determine whether the page works.

Example:

```python
page = admin_ui.list(Product)

assert page.works
```

The definition of `works` should represent successful handling of the requested admin page
according to its normal expected behavior.

---

## 6.1 Access outcome (done)

The outcome of requesting a page is a first-class value.

A page either worked, was refused, was not there, or sent the user somewhere else:

```python
assert page.works
assert page.denied
assert page.missing
assert page.redirected
assert page.destination
```

`works` means the page loaded where it was asked for. Landing on a different page is never
`works`, however that page loaded.

The admin refuses access in more than one way, and not every refusal changes the destination:

* an unauthenticated or non-staff user is sent to the login page;
* a user who may not act on a particular model is refused in place, with the destination
  unchanged.

`denied` must be true for both, not only for the one that moves the user.

A missing object is a separate outcome, `missing`, not a refusal. The admin checks permission
before existence, so a user who may not act on a model is refused without learning whether the
object exists; a user who may is sent to the index with a message that the object does not
exist. A URL the admin does not serve at all is also `missing`. Keeping `missing` apart from
`denied` matters for tests: an assertion that a user is refused must not pass because the
object was never created.

Anything else that is not `works`, such as a server error, is none of the above, and the
response status of section 6.4 says what it was.

Recognizing the refusals that leave the destination unchanged requires the response status,
which section 6.4 makes part of the contract for exactly this reason.

---

## 6.2 Page identity

Pages expose the title and subtitle the admin renders for them:

```python
page = admin_ui.edit(product)

assert page.title == "Change product"
assert page.subtitle == "Widget"
```

---

## 6.3 Admin URLs

Every admin page is addressable without being opened.

The package exposes a URL for each operation of this section:

```python
admin_ui.url.index()           # done

admin_ui.url.list(Model)       # done
admin_ui.url.create(Model)     # done
admin_ui.url.edit(instance)    # done
admin_ui.url.delete(instance)  # done
```

These are the values a test compares a link target against:

```python
assert page.row(1).cell("Customer").link == admin_ui.url.edit(customer)
```

URLs resolve through the admin site under test and its URL prefix. The package never assumes a
location, so a project that mounts its admin elsewhere gets correct URLs without changing its
tests. See section 28.2. (done)

Link targets read from a page are normalized so that they compare equal to the URL the package
produces for the same page, whether the page rendered that target in relative or absolute form.
A test must never need to know which form was rendered.

Resolution does not require the page to exist or to be reachable. Asking for the URL of a page
the current user may not open still returns that URL; whether the page works is the separate
question of section 6.1. (done)

A model the admin site does not register has no URLs. The package must report that rather than
produce a value that cannot work. (done)

Every URL above is a path. For the rare test that must hand a full URL to something outside the
package, the session turns a path into one against the server under test:

```python
admin_ui.absolute(admin_ui.url.login())
```

Opening a page never needs this; see section 6.5. (done)

---

## 6.4 Underlying access (done)

The response status of a page is part of the public contract:

```python
assert page.status_code == 200
```

Section 6.1 depends on it: some refusals are visible only in the status.

The page's native handle is available for anything the package does not model, as described in
section 3.6:

```python
page.native
```

---

## 6.5 Arbitrary admin pages

Any admin URL can be opened, including views the package knows nothing about:

```python
page = admin_ui.open(reverse("admin:shop_product_import"))    # done

assert page.works                                             # done
assert page.title == "Import products"
```

Everything beyond that is reached through `page.native`.

Such a page guarantees what does not depend on knowing the page's shape:

* the access outcome of section 6.1 (done);
* the page identity of section 6.2;
* the response status of section 6.4 (done);
* the operation messages of section 22;
* a native handle (done).

It does not expose fields or rows. Their shape is unknowable for a page the package has never
seen, and guessing would be worse than declining.

---

# 7. List / Changelist Testing

## 7.1 Column headers

The package must expose normalized changelist column headers.

Example:

```python
page = admin_ui.list(Customer)

assert page.headers == [
    "ID",
    "First name",
    "Last name",
    "Email",
]
```

It must also support subset checks:

```python
assert page.has_header("First name")
assert page.has_header("Email")
```

And:

```python
assert {"First name", "Last name"} <= set(page.headers)
```

Header matching uses the human-readable labels rendered by the admin page.

---

## 7.2 Column identity

Columns are also addressable by the names the admin is configured with:

```python
assert page.columns == [
    "id",
    "first_name",
    "last_name",
    "email",
]
```

A test chooses the vocabulary it prefers. Both must address the same columns in the same order.

---

# 8. Changelist Result Set

## 8.1 Record count

The number of records the changelist reports must be available as a number:

```python
page = admin_ui.list(Product)

assert page.count == 3
```

Where the admin renders a count summary, its normalized text is also available:

```python
assert page.summary == "3 products"
```

Tests that only care about the number should assert `page.count`, because summary wording
varies with singular and plural forms and between Django versions.

---

## 8.2 Empty changelist

An empty changelist is an explicit, assertable state:

```python
page = admin_ui.list(Product)

assert page.works
assert page.empty
assert page.count == 0
assert page.rows == []
```

---

# 9. Changelist Row Matching

One of the main 1.0.0 features is concise verification of rows shown on a changelist.

Example:

```python
assert page.contains([
    (1, "Jane", "Doe", "", ANY, some_callable),
    ANY_ROW,
])
```

## 9.1 Matcher vocabulary

Expected values are matched using three things, and nothing else:

* literal values, compared for equality;
* the sentinels `ANY` and `ANY_ROW`;
* callables.

No string value carries matcher meaning. A string in an expected row is always a literal value.

---

## 9.2 Literal values

Literal values require equality.

```python
("Jane", "Doe")
```

means that the corresponding cells must contain exactly those expected normalized values.

---

## 9.3 Empty value

An explicitly provided empty value:

```python
""
```

means that the corresponding cell is expected to be empty after normalization.

It is distinct from `ANY`.

---

## 9.4 Any-value matcher

The package must expose a sentinel representing:

> A cell must exist, but its contents are irrelevant.

Public name:

```python
ANY
```

Example:

```python
(1, "Jane", "Doe", ANY)
```

`ANY` is the only spelling for this matcher.

A literal `"*"` appearing in an expected row is an ordinary literal value and carries no matcher
meaning.

---

## 9.5 Callable matcher

A callable may be supplied for a cell.

Example:

```python
def valid_email(row, column):
    return column.endswith("@example.com")


assert page.contains([
    (1, "Jane", "Doe", valid_email),
])
```

The callable receives contextual data.

The minimum callable signature should be:

```python
matcher(current_row, current_column)
```

It returns a truthy value for a successful match.

`current_column` represents the normalized value of the current cell.

`current_row` provides access to the complete normalized row.

A richer row object may additionally expose:

```python
current_row.values
current_row.index
current_row.object
```

where available.

---

## 9.6 Ignore entire row contents

The package must support asserting that a row exists while deliberately ignoring its values.

Sentinel:

```python
ANY_ROW
```

Example:

```python
assert page.contains([
    (1, "Jane", "Doe"),
    ANY_ROW,
])
```

This means:

* one row must match `(1, "Jane", "Doe")`;
* at least one additional row may contain arbitrary values.

`ANY_ROW` is the only spelling for an ignored row.

---

## 9.7 Cell addressing by column

Rows are also addressable by column, as described in section 3.5:

```python
assert page.row(1)["First name"] == "Jane"
assert page.row(1)["Email"] == ""
```

An expected row may be expressed the same way, in which case unlisted columns are not
constrained:

```python
assert page.contains([
    {
        "First name": "Jane",
        "Last name": "Doe",
    },
])
```

This makes it possible to assert a few meaningful columns without enumerating a wide changelist.
The sentinels and callables of section 9.1 apply to values here exactly as they do in tuples.

---

## 9.8 Normalized cell values

Cell values follow section 3.4.

Booleans normalize to booleans:

```python
assert page.row(1)["Active"] is True
```

A cell the admin renders as a link exposes both its text and its target:

```python
cell = page.row(1).cell("Customer")

assert cell.value == "Jane Doe"
assert cell.link == admin_ui.url.edit(customer)
```

Link targets are compared against the admin URLs of section 6.3.

A cell may contain several links:

```python
assert page.row(1).cell("Attachments").links == [
    ("first.pdf", "/media/first.pdf"),
    ("second.pdf", "/media/second.pdf"),
]
```

Comparing a link cell against a plain literal compares its text, so tests that do not care about
targets stay short.

---

## 9.9 Row ordering

The API should support both ordered and unordered comparisons.

Default behavior for:

```python
page.contains(...)
```

verifies existence without requiring that the expected rows describe the complete changelist.

A separate API verifies the complete ordered set:

```python
assert page.rows == [...]
```

or:

```python
assert page.matches([...])
```

Exact naming can be finalized during API design.

---

# 10. Create Page Fields

The package must expose the fields present on the create page.

Example:

```python
page = admin_ui.create(Product)

assert page.fields == {
    "name",
    "price",
    "description",
    "enabled",
}
```

Subset checks should be natural:

```python
assert "name" in page.fields
assert {"name", "price"} <= page.fields
```

Individual field access should be possible:

```python
field = page.field("name")

assert field.exists
```

A missing field should produce useful pytest failure output.

---

# 11. Edit Page Fields

The edit page must expose the same field-inspection API:

```python
page = admin_ui.edit(product)

assert "name" in page.fields
assert page.field("name").required
```

Fields expose their currently rendered value:

```python
assert page.field("name").value == "Widget"
```

---

# 12. Required and Optional Fields

The package must distinguish required and non-required admin form fields.

Example:

```python
page = admin_ui.create(Product)

assert page.field("name").required
assert not page.field("description").required
```

Convenience collections should be exposed:

```python
assert page.required_fields == {
    "name",
    "price",
}

assert page.optional_fields == {
    "description",
    "enabled",
}
```

The result must reflect the actual admin form, including custom `ModelForm` behavior, rather
than only the model field definition.

---

# 13. Field Metadata

Beyond existence and requiredness, a field exposes what the admin says about it.

## 13.1 Labels

```python
assert page.field("first_name").label == "First name"
```

Fields are addressed by name; the label is data, not an address.

---

## 13.2 Initial values

The create page exposes the values the admin starts with:

```python
page = admin_ui.create(Product)

assert page.field("enabled").value is True
assert page.field("quantity").value == 1
```

---

## 13.3 Choices

A field with a fixed set of options exposes them as value and label pairs, including the blank
option where the admin renders one:

```python
field = page.field("category")

assert field.choices == [
    ("", "---------"),
    ("1", "Tools"),
    ("2", "Toys"),
]
```

Subset checks should be natural:

```python
assert ("2", "Toys") in field.choices
```

---

## 13.4 Rendered-only fields

A field is either editable or rendered only.

A rendered-only field has no input to fill, but still has a value:

```python
field = page.field("created_at")

assert not field.editable
assert field.value == "1 January 2026"
```

Where the admin renders such a field as a link, its target is available:

```python
assert page.field("owner").link == admin_ui.url.edit(owner)
```

Rendered-only fields are never populated by section 14 and never appear in
`page.required_fields`.

---

## 13.5 Field order

Fields are exposed in the order the admin presents them:

```python
assert page.field_order == [
    "name",
    "price",
    "description",
    "enabled",
]
```

Named field groups are deferred; see section 33.

---

# 14. Form Population

The package must support automatic form population.

The caller may provide values from either:

1. a dictionary;
2. an object.

---

## 14.1 Dictionary source

Example:

```python
data = {
    "name": "Widget",
    "price": "19.99",
    "description": "Example",
}

page.populate(data)
```

Only fields represented on the current admin form should be considered.

Unrelated dictionary keys should not automatically cause a failure unless strict behavior is
explicitly requested.

---

## 14.2 Object source

An arbitrary object may be used as a value source.

Example:

```python
source = SimpleNamespace(
    name="Widget",
    price="19.99",
    description="Example",
)

page.populate(source)
```

For each relevant form field, the package resolves an attribute with the corresponding field
name.

Django model instances should naturally be usable:

```python
page.populate(product)
```

This does not imply that related objects or object graphs must automatically be serialized in
1.0.0.

---

# 15. Population Modes

Three population modes are required.

## Required fields only

```python
page.populate(
    data,
    fields="required",
)
```

Only required fields are populated.

---

## Optional fields only

```python
page.populate(
    data,
    fields="optional",
)
```

Only non-required fields are populated.

---

## All fields

```python
page.populate(
    data,
    fields="all",
)
```

All supported fields for which values are available are populated.

Recommended constants may additionally be provided:

```python
REQUIRED
OPTIONAL
ALL
```

Example:

```python
page.populate(data, fields=REQUIRED)
```

---

# 16. Form Submission

Create and edit pages must support submitting explicitly supplied or populated data.

Example:

```python
page = admin_ui.create(Product)

page.populate(data, fields="required")

result = page.submit()

assert result.success
```

A compact API may also be available:

```python
result = admin_ui.create(Product, data)

assert result.success
```

Editing:

```python
result = admin_ui.edit(product, {
    "name": "New name",
})

assert result.success
```

---

## 16.1 Submit actions

A form offers a set of actions, not a single submit.

The package exposes the standard admin actions and any further actions the admin adds:

```python
page = admin_ui.edit(product)

assert page.actions == {
    "save",
    "save_and_continue",
    "save_and_add_another",
    "delete",
}
```

Presence of a single action:

```python
assert page.has_action("save_and_continue")
assert not page.has_action("delete")
```

Any action may be invoked:

```python
result = page.submit(action="save_and_continue")
```

Actions the admin defines itself are addressed the same way:

```python
assert page.has_action("approve")

result = page.submit(action="approve")
```

Omitting `action` performs the ordinary save.

---

## 16.2 Post-submission navigation

The result reports where the admin sent the user.

Any destination can be checked directly:

```python
result = admin_ui.create(Product, data)

assert result.success
assert result.redirected_to(admin_ui.url.list(Product))
```

```python
result = page.submit(action="save_and_continue")

assert result.redirected_to(admin_ui.url.edit(product))
```

`redirected_to` accepts any admin URL of section 6.3 and compares under that section's
normalization, so a test never depends on whether the admin redirected in relative or absolute
form.

Shorthands are provided for the common destinations:

```python
assert result.redirected_to_list
assert result.redirected_to_edit(product)
```

The destination remains inspectable for anything the shorthands do not cover:

```python
assert result.destination
```

---

## 16.3 Forms with no submit actions

A form on which the admin offers no actions at all is a supported, assertable state:

```python
page = admin_ui.edit(report)

assert page.works
assert page.actions == set()
```

---

# 17. Create Validation Testing

The package must make it easy to intentionally submit invalid create forms.

Example:

```python
page = admin_ui.create(Product)

result = page.submit({
    "name": "",
})

assert not result.success
```

The result must expose validation errors independently of HTML markup.

---

# 18. Edit Validation Testing

The same validation interface must apply to edit forms.

Example:

```python
page = admin_ui.edit(product)

result = page.submit({
    "name": "",
})

assert not result.success
```

Create and edit validation should use the same public error representation.

---

# 19. Re-render After Invalid Submission

An invalid submission has two consequences a test must be able to state directly.

Nothing was written:

```python
page = admin_ui.create(Product)

result = page.submit({
    "name": "",
    "price": "19.99",
})

assert not result.success
assert not result.created
```

```python
result = admin_ui.edit(product, {
    "name": "",
})

assert not result.success
assert not result.changed
```

And the form comes back carrying what was submitted:

```python
assert result.field("price").value == "19.99"
```

The re-rendered form exposes the full field API of sections 10 to 13, so requiredness, choices,
and rendered-only state remain inspectable after a failed submission.

---

# 20. Validation Error Model

Validation errors are divided into three levels:

* the summary notice the admin displays;
* form-level errors that belong to no single field;
* field-level errors.

Example:

```python
result = page.submit(...)

assert result.errors
```

---

## 20.1 Summary notice

The admin displays a notice when a submission fails.

```python
assert result.errors.banner
```

Its exact wording varies with the number of errors and between Django versions. A test that
only cares that the submission was rejected should assert truthiness.

Where a test does assert the text, the normalized message is available:

```python
assert result.errors.banner == "Please correct the error below."
```

---

## 20.2 Form-level errors

Validation messages that belong to the form rather than to any single field are exposed
separately from the summary notice:

```python
assert result.errors.non_field == [
    "At least one plan must be default.",
]
```

The summary notice and form-level errors are distinct concepts and must not be conflated.

---

## 20.3 Field errors

Errors for an individual field should be accessible by field name.

Example:

```python
assert "This field is required." in result.errors["name"]
```

Multiple errors must be supported:

```python
assert result.errors["email"] == [
    "Enter a valid email address.",
]
```

Convenience access may also be provided:

```python
assert result.field("email").errors == [
    "Enter a valid email address.",
]
```

---

# 21. Validation Error Matching

Tests should be able to perform both exact and partial validation checks.

Exact:

```python
assert result.errors["name"] == [
    "This field is required.",
]
```

Contains:

```python
assert "This field is required." in result.errors["name"]
```

Complete error-set testing:

```python
assert result.errors.fields == {
    "name": ["This field is required."],
    "email": ["Enter a valid email address."],
}
```

---

# 22. Operation Messages

The admin reports the outcome of an operation to the user.

Messages are exposed with their level and their normalized text, independently of markup:

```python
result = admin_ui.create(Product, data)

assert result.messages == [
    ("success", "The product “Widget” was added successfully."),
]
```

Level-based access should also be natural:

```python
assert result.messages.success
assert not result.messages.error
```

Messages are distinct from validation errors. A successful operation produces messages and no
errors; a rejected operation produces errors and may produce no messages at all.

---

# 23. CRUD Success Checks

The package must support basic create, edit, and delete workflows.

## 23.1 Create

```python
result = admin_ui.create(Product, {
    "name": "Widget",
    "price": "10.00",
})

assert result.success
```

Operation results expose the affected object:

```python
product = result.object

assert product.name == "Widget"
```

---

## 23.2 Edit

```python
result = admin_ui.edit(product, {
    "name": "Updated widget",
})

assert result.success
assert result.object.name == "Updated widget"
```

The object exposed by an edit result reflects the stored state after the operation.

---

## 23.3 Delete

```python
result = admin_ui.delete(product)

assert result.success
```

---

## 23.4 Delete confirmation contents

The confirmation page exposes the objects the admin says will be removed, including related
ones:

```python
page = admin_ui.delete(customer)

assert page.works

assert customer in page.objects
assert len(page.objects) == 3
```

---

## 23.5 Deletion refused

An admin may decline to offer or to perform a deletion.

The absence of the action is assertable:

```python
page = admin_ui.edit(product)

assert not page.has_action("delete")
```

So is a refused operation:

```python
result = admin_ui.delete(product)

assert not result.success
```

---

# 24. Admin Index and Model Exposure

The package must expose what the admin presents to the current user.

```python
page = admin_ui.index()    # done

assert page.works          # done
```

Which models are exposed:

```python
assert Product in page.models
assert Category in page.models
```

How they are grouped, in the order presented:

```python
assert page.apps == [
    "Shop",
    "Authentication and Authorization",
]

assert page.models_for("Shop") == [
    Product,
    Category,
]
```

Model exposure reflects the current user. A model the user may not see is not listed.

---

# 25. Page Object Model

The public API should conceptually expose these page/result types.

```text
AdminSession
│
├── AdminUrls
│
├── AdminPage            (any admin URL — section 6.5)
├── AdminIndexPage
├── ChangelistPage
├── CreatePage
├── EditPage
├── DeletePage
│
├── FormField
│   └── FieldChoice
├── SubmitActions
├── Row
├── Cell
├── Permissions
│
└── SubmissionResult
    ├── ValidationErrors
    └── Messages
```

The exact Python class names are implementation details, but the public concepts should remain
recognizable and stable.

Every type listed above exposes a native handle, as described in section 3.6.

---

# 26. Example 1.0.0 Tests

## Authentication and permissions

```python
def test_staff_access(admin_ui, staff_user):
    admin_ui.login(staff_user)

    permissions = admin_ui.permissions(Product)

    assert permissions.view
    assert permissions.change
    assert not permissions.delete
```

---

## Basic page health

```python
def test_product_admin_pages(admin_ui, admin_user, product):
    admin_ui.login(admin_user)

    assert admin_ui.list(Product).works
    assert admin_ui.create(Product).works
    assert admin_ui.edit(product).works
    assert admin_ui.delete(product).works
```

---

## Model exposure

```python
def test_shop_models_are_exposed(admin_ui, admin_user):
    admin_ui.login(admin_user)

    page = admin_ui.index()

    assert page.models_for("Shop") == [
        Product,
        Category,
    ]
```

---

## Changelist

```python
def test_customer_list(admin_ui, admin_user):
    admin_ui.login(admin_user)

    page = admin_ui.list(Customer)

    assert page.count == 3

    assert page.headers == [
        "ID",
        "First name",
        "Last name",
        "Email",
        "Status",
    ]

    assert page.contains([
        (
            1,
            "Jane",
            "Doe",
            "",
            ANY,
        ),
        (
            2,
            "John",
            "Doe",
            lambda row, value: "@" in value,
            ANY,
        ),
        ANY_ROW,
    ])
```

---

## Changelist by column

```python
def test_customer_status(admin_ui, admin_user):
    admin_ui.login(admin_user)

    page = admin_ui.list(Customer)

    assert page.contains([
        {
            "First name": "Jane",
            "Active": True,
        },
    ])
```

---

## Empty changelist

```python
def test_empty_customer_list(admin_ui, admin_user):
    admin_ui.login(admin_user)

    page = admin_ui.list(Customer)

    assert page.works
    assert page.empty
    assert page.count == 0
```

---

## Form structure

```python
def test_product_create_fields(admin_ui, admin_user):
    admin_ui.login(admin_user)

    page = admin_ui.create(Product)

    assert page.fields == {
        "name",
        "price",
        "description",
        "enabled",
    }

    assert page.field("name").required
    assert page.field("price").required
    assert not page.field("description").required

    assert page.field("name").label == "Name"
    assert page.field("enabled").value is True

    assert page.field("category").choices == [
        ("", "---------"),
        ("1", "Tools"),
        ("2", "Toys"),
    ]
```

---

## Rendered-only fields

```python
def test_report_is_read_only(admin_ui, admin_user, report):
    admin_ui.login(admin_user)

    page = admin_ui.edit(report)

    assert not page.field("created_at").editable
    assert page.actions == set()
```

---

## Required-field population

```python
def test_create_product(admin_ui, admin_user):
    admin_ui.login(admin_user)

    page = admin_ui.create(Product)

    page.populate({
        "name": "Widget",
        "price": "12.00",
        "description": "Ignored",
    }, fields="required")

    result = page.submit()

    assert result.success
    assert result.redirected_to_list
    assert result.messages.success
```

---

## Validation

```python
def test_product_validation(admin_ui, admin_user):
    admin_ui.login(admin_user)

    page = admin_ui.create(Product)

    result = page.submit({
        "name": "",
        "price": "",
    })

    assert not result.success
    assert not result.created

    assert result.errors.banner

    assert result.errors["name"] == [
        "This field is required.",
    ]

    assert result.errors["price"] == [
        "This field is required.",
    ]
```

---

## Re-render after an invalid submission

```python
def test_product_form_is_rendered_back(admin_ui, admin_user):
    admin_ui.login(admin_user)

    page = admin_ui.create(Product)

    result = page.submit({
        "name": "",
        "price": "12.00",
    })

    assert not result.success
    assert not result.created

    assert result.field("price").value == "12.00"
```

---

# 27. Public Fixtures

The package exposes a primary pytest fixture (done):

```python
admin_ui
```

Example:

```python
def test_something(admin_ui, admin_user):
    admin_ui.login(admin_user)
```

The name is deliberately explicit. It names what is under test rather than how it is driven, and
it does not collide with project fixtures named `admin` or with the `admin` module imported in
most Django test modules.

The fixture is parameterizable for the admin site described in sections 28 and 29. (done)

Public names are importable from the module that defines them:

```python
from django_admin_kit.pages import AdminPage
```

The package root exports nothing else. It is imported at pytest startup by every project that
installs the package, and must stay free of anything that loads the admin or the browser. (done)

Two guarantees hold for every test that uses the fixture:

* **Each test begins unauthenticated.** No session, cookie, or page state established by one
  test is visible to another, whatever order tests run in. (done)
* **Tests are safe to run in parallel.** Nothing the fixture provides is shared between
  concurrently running tests. (done)

A test that uses the fixture is identified by the browser it ran on as well as by its name, so
asking for two browsers runs it twice. That follows from taking the browser from the established
plugin rather than owning one (section 28.4), and it means test identifiers change for a project
adopting this package. (done)

---

# 28. Configuration and Extensibility

The package must be generic and adjustable to every project's needs.

Nothing project-specific ships in the package. Every project-specific behavior enters through a
documented extension point.

## 28.1 Configuration surface

Project-wide defaults are set in one place, so individual tests stay free of setup noise.

All settings live under a single key:

```python
DJANGO_ADMIN_KIT = {
    ...
}
```

Configurable at minimum:

* the admin site under test (done);
* how long any single browser operation may take, and the time zone and locale the browser
  reports (done);
* value normalization;
* field handling.

How the browser itself is chosen and shown is **not** configured here. See section 28.4. (done)

---

## 28.2 Admin location

The admin URL prefix is **not** assumed to be `/admin/`. URLs are resolved from the admin site
under test. (done)

---

## 28.3 Normalization rules

All normalization described in section 3.4 is defined by settings, not by package internals.

The package ships a complete default rule set. At minimum it covers:

* booleans;
* empty and absent values;
* links, and their targets;
* dates and times;
* numbers;
* the display value of a choice;
* surrounding text and whitespace.

Every rule in that set has a documented default and is individually addressable:

```python
DJANGO_ADMIN_KIT = {
    "normalizers": {
        "boolean": ...,
        "empty": ...,
        "link": ...,
        "datetime": ...,
        "number": ...,
        "choice": ...,
        "text": ...,
    },
}
```

Three things must hold:

* **Any rule can be overridden.** A project replaces a single rule without restating the rest.
  The defaults it does not mention stay in force.
* **New rules can be added.** A project registers normalization for a representation the package
  does not know, and that representation then behaves like any other.
* **No rule is privileged.** Nothing is hardcoded, and no override requires modifying or
  subclassing package internals.

Overrides apply project-wide by default. It must also be possible to override a rule for a
single test, so that a test covering unusual rendering does not force a project-wide change:

```python
admin_ui.normalizer("boolean", my_boolean_rule)
```

---

## 28.4 Browser settings (done)

The package does not own the browser. It takes one from the established pytest plugin for
browser testing, and that plugin's own options decide which browser runs, whether it is visible,
how far it is slowed down, and what is recorded while it runs.

This is deliberate. A project that already tests through a browser has those options set and its
authors know them; a second vocabulary meaning the same thing would give every such project two
places to say one thing, and a test suite converted to this package would have to be reconfigured
to get behaviour it already had.

What remains under `DJANGO_ADMIN_KIT` is what the package itself decides:

```python
DJANGO_ADMIN_KIT = {
    "site": ...,
    "timeout": ...,
    "timezone": ...,
    "locale": ...,
}
```

`timeout` bounds any single browser operation. `timezone` and `locale` pin the zone and the
language the browser reports, so results do not depend on the machine running the tests, per
section 31. They default to the project's own `TIME_ZONE` and `LANGUAGE_CODE`.

Two consequences follow from not owning the browser. The package inherits whatever that plugin
does to a test session, including behaviour a project did not ask for, and adopting the package
means adopting it. And a test's identity carries the browser it ran on, per section 27.

Configuration errors must be loud. An unrecognized setting is rejected, naming the key and
listing the valid ones, because a silently accepted typo disables a setting invisibly. A setting
that used to be part of this package and has since moved is therefore reported as unknown rather
than ignored. Settings are validated once, before the first page is opened, not at the moment
each is first read.

---

## 28.5 Field handling hooks

A project must be able to teach the package how to read and how to fill a field representation
the package does not know.

Once registered, such a field participates in field inspection, population, and submission like
any other.

---

## 28.6 Project-defined helpers

The package provides **no mechanism** for registering project-specific page classes, and this is
a decision rather than an omission.

A project that wants named operations for its own admin views writes ordinary Python around the
pages the package returns — a function, or a class of its own that takes a page:

```python
def import_products(page, path):
    """Written by the project, in terms of the page's native handle."""
    page.native.fill("#id_file", path)
    page.native.click("#import-submit")


import_products(admin_ui.open(import_url), "products.csv")
```

Nothing about this requires the package's cooperation, which is why the package does not offer
any. Should a registration mechanism prove worth having, adding one would be purely additive.

---

## 28.7 No required base class

No assertion, matcher, or page object may require a project to subclass a package-provided test
case in order to be used.

This preserves the reuse principle of section 3.7: a project composes its own reusable
expectations however it prefers.

---

# 29. Custom Django Admin Sites

The architecture must allow tests to target a non-default `AdminSite`.

A project with one admin names it once, in the configuration of section 28:

```python
DJANGO_ADMIN_KIT = {
    "site": "project.ops.ops_site",
}
```

A project with several admins overrides the fixture that resolves the site's URLs, at whatever
scope pytest allows a fixture to be overridden, so a module or class of tests targets one site
while the rest of the suite keeps the default:

```python
@pytest.fixture
def admin_ui_urls():
    return AdminUrls(ops_site)
```

The site is fixed for the life of a test. Nothing switches sites inside one. (done)

Support for custom AdminSite instances, including sites mounted under a non-default URL prefix,
is part of a 1.0.0 architectural requirement even if the default site is the common path. (done)

---

# 30. Error Reporting

Failure output is an important part of the library.

For example, instead of a generic:

```text
AssertionError
```

a changelist mismatch should expose information such as:

```text
Expected row:
    [1, "Jane", "Doe", ANY]

No matching row found.

Actual rows:
    [1, "Janet", "Doe", "Active"]
    [2, "John", "Doe", "Inactive"]
```

A form-field failure should similarly make expected and actual state visible:

```text
Expected field "email" to be required.

Actual:
    required=False
```

The library should make normal pytest assertion rewriting useful rather than hiding failures
behind opaque helper exceptions.

---

# 31. Compatibility Requirement

The minimum supported versions are:

```text
Django 3.2
Python 3.8
```

(done)

The package architecture must support testing multiple later Django releases without exposing
version-specific behavior through the public API. (done)

A user test such as:

```python
assert admin_ui.list(Product).works
```

or:

```python
assert page.contains([...])
```

should remain unchanged across supported Django versions.

Version-specific normalization belongs inside the package. This includes differences in how
values are rendered and, where practical, differences in the wording of the admin's own
built-in messages.

Values render through the formats and time zone the project has configured. Tests must never
hardcode a rendering format in order to pass.

Results must not depend on the machine a test runs on. The browser carries its own notion of
locale and time zone, and the package pins both to what the project has configured, so the same
test yields the same values everywhere. (done)

Where a project has already pinned one of them for its own browser tests, that setting stands.
The package fills in what is unset rather than overriding a deliberate choice, so a project
cannot end up with admin tests running in a different zone from the rest of its suite. (done)

---

# 32. 1.0.0 Acceptance Criteria

1.0.0 is considered complete when a test project can demonstrate all of the following against
supported Django versions:

1. Log in with a superuser. (done)
2. Log in with a staff user. (done)
3. Log in with an arbitrary user object, including one that has no usable password. (done)
4. Determine view/add/change/delete permissions for a model.
5. Determine a permission a model declares beyond the standard four, and read the
   complete effective permission set.
6. Determine effective permissions where the admin imposes constraints of its own.
7. Determine permissions for an individual object.
8. Verify that a page the user may not open is reported as refused. (done)
9. Verify that model changelist, create, edit, and delete pages work.
10. Read a page's title and subtitle.
11. Read changelist headers, by label and by configured column name.
12. Read the changelist record count and assert an empty changelist.
13. Verify changelist rows using:

    * exact values;
    * empty values;
    * `ANY`;
    * callable cell matchers;
    * `ANY_ROW`;
    * column-addressed expected rows.
14. Read normalized boolean cells, empty cells, and link cells including their targets.
15. Inspect fields on create and edit pages.
16. Determine required and optional fields.
17. Read field labels, initial values, choices, and presentation order.
18. Distinguish editable from rendered-only fields and read a rendered-only value.
19. Populate required fields only.
20. Populate optional fields only.
21. Populate all supported fields.
22. Populate from a dictionary.
23. Populate from an object.
24. Submit valid create forms.
25. Submit valid edit forms.
26. Invoke a submit action other than the ordinary save, including one the admin defines.
27. Determine where the admin navigated after a successful operation.
28. Submit invalid create forms.
29. Submit invalid edit forms.
30. Verify that an invalid submission wrote nothing and that the form rendered the submitted
    values back.
31. Inspect the admin's summary notice, form-level errors, and field-level errors as three
    distinct levels.
32. Read the messages displayed after an operation.
33. Perform and verify a basic delete operation.
34. Read the contents of a deletion confirmation.
35. Verify that a refused deletion is not offered or not performed.
36. Read the models the admin exposes to the current user, their grouping, and their order.
37. Run against a non-default admin site mounted under a non-default URL prefix. (done)
38. Override a default normalization rule, add a new one, and extend field handling from a
    project, without subclassing package internals.
39. Reach a native handle from a page and from a field, and drive a project-specific widget
    with it.
40. Open an arbitrary admin URL and read its access outcome and identity.
41. Run the test suite in parallel. (done)
42. Run the same public test syntax starting with Django 3.2.

---

# 33. Roadmap Beyond 1.0.0

## 1.1.0 — Relational and compound forms

* many-to-many fields;
* one-to-many relationships;
* Django Admin inlines;
* stacked inlines;
* tabular inlines;
* inline shape, including the row counts and the initial, minimum, and maximum the admin
  declares;
* inline creation, editing, and deletion;
* inline validation errors at cell, row, and formset granularity;
* rendered-only inlines;
* related-object automatic population;
* named field groups.

---

## 1.2.0 — Changelist interaction

* changelist search;
* filters;
* ordering and sortable columns;
* pagination and page traversal;
* actions;
* `list_editable`.

---

## 1.3.0 — Advanced form surfaces

* autocomplete fields;
* raw-ID fields;
* horizontal and vertical selectors;
* date hierarchy;
* file and image upload fields;
* custom and rich field representations;
* conditionally displayed fields;
* dependent choice sets.

---

## Later

* custom admin views and endpoints beyond the standard operations;
* richer row and cell matchers;
* verifying side effects triggered by an admin operation.
