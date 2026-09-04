# Django Admin Testing Package — v0.1 Specification

## 1. Purpose

The package provides a pytest-oriented API for testing Django Admin behavior.

It should allow developers to verify:

* authentication and access with different users;
* model-level admin permissions;
* availability and basic operation of admin pages;
* create and edit form validation;
* changelist columns and row contents;
* create/edit form fields and requiredness;
* automatic population of form fields;
* validation errors displayed by Django Admin.

The package should emphasize readable tests using normal Python `assert` statements rather than custom assertion methods wherever practical.

The minimum supported Django version is **Django 3.2**.

---

# 2. Scope of v0.1

v0.1 covers standard Django Admin functionality for simple models.

Supported relationships and field behavior should be limited to fields that can be represented as ordinary scalar form values.

The following are explicitly deferred to a later version:

* many-to-many form fields;
* one-to-many/inlines;
* inline formsets;
* complex custom admin widgets;
* advanced admin actions;
* advanced changelist filters;
* JavaScript-specific behavior.

Foreign keys may be supported where they behave as a normal single-value form field, but automatic traversal or creation of related object graphs is not required for v0.1.

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

Where failure diagnostics require more context, objects returned by the library should implement useful comparison behavior and pytest assertion introspection where possible.

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

Tests should interact with package-level abstractions rather than depending directly on Django Admin internals.

Typical concepts exposed by the package:

```python
admin
admin.login(...)
admin.permissions(...)
admin.list(...)
admin.create(...)
admin.edit(...)
admin.delete(...)
```

Page objects should expose normalized information such as fields, errors, headers, rows, and status.

---

# 4. Authentication

The package must support using any Django user object.

At minimum:

```python
admin.login(admin_user)
admin.login(staff_user)
admin.login(arbitrary_user)
```

The package must not assume that:

* the user model uses `username`;
* the default Django `User` model is installed;
* only superusers can access Admin.

An arbitrary custom user model must therefore be usable as long as the Django project itself supports it.

Example:

```python
admin.login(user)

page = admin.index()

assert page.works
```

The test author must also be able to switch users during a test:

```python
admin.login(user_a)
...
admin.login(user_b)
...
```

Logout should also be available:

```python
admin.logout()
```

---

# 5. Permission Testing

The package must expose the effective Django Admin permissions of a user for a model.

Supported permissions:

* view;
* add;
* change;
* delete.

Example API:

```python
permissions = admin.permissions(Product)

assert permissions.view
assert permissions.add
assert permissions.change
assert not permissions.delete
```

A compact form should also be possible:

```python
assert admin.permissions(Product) == {
    "view": True,
    "add": True,
    "change": True,
    "delete": False,
}
```

Permission checks must represent the permissions applicable to the currently logged-in user.

The API should also support permission testing without requiring the corresponding page to be opened.

---

# 6. Admin Page Availability

The package must provide abstractions for these four standard model admin operations:

```python
admin.list(Model)
admin.create(Model)
admin.edit(instance)
admin.delete(instance)
```

Each returned page must make it easy to determine whether the page works.

Example:

```python
page = admin.list(Product)

assert page.works
```

The definition of `works` should represent successful handling of the requested admin page according to its normal expected behavior.

Tests must also be able to inspect lower-level information when necessary, for example:

```python
assert page.status_code == 200
```

The original underlying response should remain accessible:

```python
page.response
```

---

# 7. List / Changelist Testing

## 7.1 Column headers

The package must expose normalized changelist column headers.

Example:

```python
page = admin.list(Customer)

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

Header matching should use the human-readable labels rendered by the admin page unless an explicitly different API is provided for field/configuration names.

---

# 8. Changelist Row Matching

One of the main v0.1 features is concise verification of rows shown on a changelist.

Example:

```python
assert page.contains([
    (1, "Jeff", "Bezos", "", ANY, some_callable),
    ANY_ROW,
])
```

The row matcher must support several value types.

## 8.1 Literal values

Literal values require equality.

```python
("Jeff", "Bezos")
```

means that the corresponding cells must contain exactly those expected normalized values.

---

## 8.2 Empty value

An explicitly provided empty value:

```python
""
```

means that the corresponding cell is expected to be empty after normalization.

It is distinct from `ANY`.

---

## 8.3 Any-value matcher

The package must expose a sentinel representing:

> A cell must exist, but its contents are irrelevant.

Recommended public name:

```python
ANY
```

Example:

```python
(1, "Jeff", "Bezos", ANY)
```

The equivalent textual representation may be `"*"`, but a dedicated Python sentinel is preferred so that literal `*` values remain testable.

---

## 8.4 Callable matcher

A callable may be supplied for a cell.

Example:

```python
def valid_email(row, column):
    return column.endswith("@example.com")


assert page.contains([
    (1, "Jeff", "Bezos", valid_email),
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

## 8.5 Ignore entire row contents

The package must support asserting that a row exists while deliberately ignoring its values.

Recommended sentinel:

```python
ANY_ROW
```

Example:

```python
assert page.contains([
    (1, "Jeff", "Bezos"),
    ANY_ROW,
])
```

This means:

* one row must match `(1, "Jeff", "Bezos")`;
* at least one additional row may contain arbitrary values.

If a sequence representation such as:

```python
["*"]
```

is supported for convenience, it should normalize internally to `ANY_ROW`.

---

## 8.6 Row ordering

The API should support both ordered and unordered comparisons.

Default behavior for:

```python
page.contains(...)
```

should verify existence without requiring that the expected rows describe the complete changelist.

A separate API may verify the complete ordered set:

```python
assert page.rows == [...]
```

or:

```python
assert page.matches([...])
```

Exact naming can be finalized during API design.

---

# 9. Create Page Fields

The package must expose the fields present on the create page.

Example:

```python
page = admin.create(Product)

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

# 10. Edit Page Fields

The edit page must expose the same field-inspection API:

```python
page = admin.edit(product)

assert "name" in page.fields
assert page.field("name").required
```

Where appropriate, fields should additionally expose their currently rendered value:

```python
assert page.field("name").value == "Widget"
```

---

# 11. Required and Optional Fields

The package must distinguish required and non-required admin form fields.

Example:

```python
page = admin.create(Product)

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

The result must reflect the actual admin form, including custom `ModelForm` behavior, rather than only the model field definition.

---

# 12. Form Population

The package must support automatic form population.

The caller may provide values from either:

1. a dictionary;
2. an object.

---

## 12.1 Dictionary source

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

Unrelated dictionary keys should not automatically cause a failure unless strict behavior is explicitly requested.

---

# 13. Object source

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

For each relevant form field, the package resolves an attribute with the corresponding field name.

Django model instances should naturally be usable:

```python
page.populate(product)
```

This does not imply that related objects or object graphs must automatically be serialized in v0.1.

---

# 14. Population Modes

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

# 15. Form Submission

Create and edit pages must support submitting explicitly supplied or populated data.

Example:

```python
page = admin.create(Product)

page.populate(data, fields="required")

result = page.submit()

assert result.success
```

A compact API may also be available:

```python
result = admin.create(Product, data)

assert result.success
```

Editing:

```python
result = admin.edit(product, {
    "name": "New name",
})

assert result.success
```

---

# 16. Create Validation Testing

The package must make it easy to intentionally submit invalid create forms.

Example:

```python
page = admin.create(Product)

result = page.submit({
    "name": "",
})

assert not result.success
```

The result must expose validation errors independently of HTML markup.

---

# 17. Edit Validation Testing

The same validation interface must apply to edit forms.

Example:

```python
page = admin.edit(product)

result = page.submit({
    "name": "",
})

assert not result.success
```

Create and edit validation should use the same public error representation.

---

# 18. Validation Error Model

Validation errors must be divided into:

* page/form-level errors;
* field-level errors.

Example:

```python
result = page.submit(...)

assert result.errors
```

---

## 18.1 Header / form-level validation messages

Messages displayed globally by the form should be exposed as a normalized collection.

Example:

```python
assert "Please correct the errors below." in result.errors.header
```

The package should distinguish rendered summary/header messages from individual field validation messages.

---

## 18.2 Field errors

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

# 19. Validation Error Matching

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

# 20. CRUD Success Checks

The package must support basic create, edit, and delete workflows.

Create:

```python
result = admin.create(Product, {
    "name": "Widget",
    "price": "10.00",
})

assert result.success
```

Edit:

```python
result = admin.edit(product, {
    "name": "Updated widget",
})

assert result.success
```

Delete:

```python
result = admin.delete(product)

assert result.success
```

Where practical, operation results should expose the affected object:

```python
result.object
```

For create operations this enables:

```python
product = result.object

assert product.name == "Widget"
```

---

# 21. Page Object Model

The public API should conceptually expose these page/result types.

```text
AdminSession
│
├── AdminIndexPage
├── ChangelistPage
├── CreatePage
├── EditPage
├── DeletePage
│
├── FormField
├── Row
├── Cell
├── Permissions
│
└── SubmissionResult
    └── ValidationErrors
```

The exact Python class names are implementation details, but the public concepts should remain recognizable and stable.

---

# 22. Example v0.1 Tests

## Authentication and permissions

```python
def test_staff_access(admin, staff_user):
    admin.login(staff_user)

    permissions = admin.permissions(Product)

    assert permissions.view
    assert permissions.change
    assert not permissions.delete
```

---

## Basic page health

```python
def test_product_admin_pages(admin, admin_user, product):
    admin.login(admin_user)

    assert admin.list(Product).works
    assert admin.create(Product).works
    assert admin.edit(product).works
    assert admin.delete(product).works
```

---

## Changelist

```python
def test_customer_list(admin, admin_user):
    admin.login(admin_user)

    page = admin.list(Customer)

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
            "Jeff",
            "Bezos",
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

## Form structure

```python
def test_product_create_fields(admin, admin_user):
    admin.login(admin_user)

    page = admin.create(Product)

    assert page.fields == {
        "name",
        "price",
        "description",
        "enabled",
    }

    assert page.field("name").required
    assert page.field("price").required
    assert not page.field("description").required
```

---

## Required-field population

```python
def test_create_product(admin, admin_user):
    admin.login(admin_user)

    page = admin.create(Product)

    page.populate({
        "name": "Widget",
        "price": "12.00",
        "description": "Ignored",
    }, fields="required")

    result = page.submit()

    assert result.success
```

---

## Validation

```python
def test_product_validation(admin, admin_user):
    admin.login(admin_user)

    page = admin.create(Product)

    result = page.submit({
        "name": "",
        "price": "",
    })

    assert not result.success

    assert "Please correct the errors below." in result.errors.header

    assert result.errors["name"] == [
        "This field is required.",
    ]

    assert result.errors["price"] == [
        "This field is required.",
    ]
```

---

# 23. Public Fixtures

The package should expose a primary pytest fixture.

Working name:

```python
admin
```

Example:

```python
def test_something(admin, admin_user):
    admin.login(admin_user)
```

If `admin` proves too likely to conflict with project fixtures, a more explicit public name should be chosen before the first stable release, for example:

```python
django_admin
```

Fixture naming should be finalized before v0.1 to avoid later backwards-incompatible renaming.

---

# 24. Custom Django Admin Sites

The architecture must allow tests to target a non-default `AdminSite`.

Example target API:

```python
admin.use_site(custom_admin_site)
```

or through configuration/fixture construction.

Support for custom AdminSite instances is part of the v0.1 architectural requirement even if the default site is the common path.

---

# 25. Error Reporting

Failure output is an important part of the library.

For example, instead of a generic:

```text
AssertionError
```

a changelist mismatch should expose information such as:

```text
Expected row:
    [1, "Jeff", "Bezos", ANY]

No matching row found.

Actual rows:
    [1, "Jeffrey", "Bezos", "Active"]
    [2, "John", "Doe", "Inactive"]
```

A form-field failure should similarly make expected and actual state visible:

```text
Expected field "email" to be required.

Actual:
    required=False
```

The library should make normal pytest assertion rewriting useful rather than hiding failures behind opaque helper exceptions.

---

# 26. Compatibility Requirement

The minimum supported Django version is:

```text
Django 3.2
```

The package architecture must support testing multiple later Django releases without exposing version-specific behavior through the public API.

A user test such as:

```python
assert admin.list(Product).works
```

or:

```python
assert page.contains([...])
```

should remain unchanged across supported Django versions.

Version-specific normalization belongs inside the package.

---

# 27. v0.1 Acceptance Criteria

v0.1 is considered complete when a test project can demonstrate all of the following against supported Django versions:

1. Log in with a superuser.
2. Log in with a staff user.
3. Log in with an arbitrary user object.
4. Determine view/add/change/delete permissions for a model.
5. Verify that model changelist, create, edit, and delete pages work.
6. Read changelist headers.
7. Verify changelist rows using:

   * exact values;
   * empty values;
   * `ANY`;
   * callable cell matchers;
   * `ANY_ROW`.
8. Inspect fields on create and edit pages.
9. Determine required and optional fields.
10. Populate required fields only.
11. Populate optional fields only.
12. Populate all supported fields.
13. Populate from a dictionary.
14. Populate from an object.
15. Submit valid create forms.
16. Submit valid edit forms.
17. Submit invalid create forms.
18. Submit invalid edit forms.
19. Inspect form/header validation messages.
20. Inspect validation errors associated with individual fields.
21. Perform and verify a basic delete operation.
22. Run the same public test syntax starting with Django 3.2.

---

# 28. Deferred to v0.2+

The first planned expansion should cover relational and compound admin forms, particularly:

* many-to-many fields;
* one-to-many relationships;
* Django Admin inlines;
* stacked inlines;
* tabular inlines;
* related-object automatic population;
* inline validation errors;
* inline creation and editing.

Other potential later features include:

* changelist search;
* filters;
* pagination;
* ordering;
* actions;
* `list_editable`;
* readonly fields;
* fieldsets;
* custom admin views;
* autocomplete fields;
* raw-ID fields;
* date hierarchy;
* richer row and cell matchers.

