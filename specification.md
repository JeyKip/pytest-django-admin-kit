# Django Admin Testing Package — 1.0.0 Specification

# 1. Purpose

The package provides a pytest-oriented API for testing Django Admin behavior.

It should allow developers to verify:

* authentication and access with different users (done);
* availability and basic operation of admin pages; (done)
* the set of models the admin exposes; (done)
* changelist columns, record counts, and row contents (done);
* create and edit form fields, including their labels, initial values, and choices (done);
* editable and rendered-only field values (done);
* requiredness of create and edit form fields (done);
* automatic population of form fields; (done)
* submit actions and where the admin navigates after an operation; (done)
* validation errors displayed by Django Admin; (done)
* what a form renders back after an invalid submission; (done)
* messages displayed after an operation; (done)
* the contents of a deletion confirmation. (done)

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

## 3.1 Pytest-style assertions (done)

Tests should look like ordinary pytest tests.

Preferred:

```python
assert page.works                          # done
assert "first_name" in page.fields         # done
assert page.fields["email"].required       # done
assert page.contains((...))                # done
```

Avoid making the primary interface:

```python
page.assertFieldExists(...)
page.assertPageWorks(...)
```

Where failure diagnostics require more context, objects returned by the library should implement
useful comparison behavior and pytest assertion introspection where possible. Where a check
has a picture to show, such as a row match, it raises `AssertionError` carrying that picture,
the way `assert_frame_equal` and `assertEqual` do, and pytest prints it line by line; the
`assert` in front of it then reads as intent and is not what fails.

---

## 3.2 Explicit over implicit (done)

Tests should clearly express:

* which user is being used;
* which model is being tested;
* which admin page is being tested;
* which values are expected;
* which values should be generated automatically.

Automatic behavior should remain predictable and inspectable.

---

## 3.3 Stable public abstraction (done)

Tests should interact with package-level abstractions rather than depending directly on Django
Admin internals.

Typical concepts exposed by the package:

```python
admin_ui                   # done
admin_ui.login(...)        # done
admin_ui.index()           # done
admin_ui.list(...)         # done
admin_ui.create(...)       # done
admin_ui.edit(...)         # done
admin_ui.delete(...)       # done
```

Page objects should expose normalized information such as fields, errors, headers, rows,
messages, and status.

---

## 3.4 Normalized values (done)

The package compares **what the user reads**, not markup.

A value read from an admin page is normalized before a test ever sees it:

* a boolean the admin draws as an icon normalizes to a boolean; (done)
* a value the admin renders as a link normalizes to its text, with the link available
  separately; (done)
* everything else is the document's own text, never its rendered presentation, so styling
  such as letter-casing never changes a value. (done)

Text is compared as rendered. A date, a number or an empty value reads as the text the admin
shows for it, in the locale and time zone the browser is pinned to (sections 28.4 and 31), so
a test asserts the rendering the user sees:

```python
assert page.rows[0]["is_active"].value is True                  # done
assert page.rows[0]["released_on"].value == "Sept. 12, 2026"    # done
```

One value on a form is not text: an option chosen from a fixed set is a pair of the value the
form posts and the label the user reads, each read by name (section 13.3). (done)

A project that wants such a value typed replaces the rule that reads it. Every normalization
rule is a package setting with a documented default, and every one of them can be replaced by
the project. Nothing about normalization is fixed inside the package. See section 28.3. (done)

---

## 3.5 Addressing by name (done)

The package uses one coordinate vocabulary everywhere it applies:

* on a changelist, rows are addressed by position, 0-based like any Python sequence, and
  cells by the name the column is configured with, as section 7.2 lists them; (done)
* on a form, fields are addressed by name. (done)

A label is what the user sees, and a test reads it as data: `page.headers` for columns,
section 13.1 for fields. It is never an address, because it is presentation, and the same
column or field keeps its name across translations and relabeling.

```python
page.rows[0]             # done
page.rows[0]["email"]    # done
page.fields["email"]     # done
```

A cell is also addressable by position, where that is the clearer expression:

```python
page.rows[0][2]    # done
```

---

## 3.6 Native access (done)

A package can only generalize what Django Admin itself renders. Every real project adds custom
admin views, overridden templates, custom widgets, and third-party admin applications, and a
test must be able to reach those.

The API therefore has two tiers, and one rule decides which applies:

> If Django Admin renders it, the package normalizes it.
> If your project renders it, you take a native handle.

Both tiers appear in the same test, without leaving the package:

```python
page = admin_ui.edit(product)

assert page.fields["name"].required            # standard field, package vocabulary (done)
page.fields["color_picker"].native.click()    # the project's own widget, native handle (done)
```

Reaching for a native handle is **expected and supported**, not a failure or a last resort. A
project keeps the package's login, navigation, URL resolution and normalization, and drops to
the browser only for the part the package cannot know about.

Native handles are available at every level of the object model:

```python
admin_ui.native                        # done
page.native                            # done
page.fields["name"].native             # done
page.rows[0].native                    # done
page.rows[0]["email"].native           # done
```

They are the underlying browser library's own objects. The package does not wrap, restrict, or
re-export them, so their type is part of this package's public surface and changes to it are
breaking changes.

---

## 3.7 Reusable page contracts (done)

Projects test many admin pages that differ only in their model and their expected shape.

Expressing a page's expected shape once and applying it to many models must be natural.

The package must not prescribe a class hierarchy, and must not require a project to subclass a
package-provided test case in order to reuse expectations.

---

## 3.8 Project-level adjustability (done)

The package ships nothing project-specific.

Every project-specific behavior enters through a documented extension point rather than through
a fork, a subclass requirement, or a special case inside the package.

See section 28.

---

## 3.9 Live reads (done)

The package keeps nothing it has read. Every value is read from the page, or from the database,
when a test asks for it, so it is what the user would see at that moment. That includes what
the admin's own scripts and a project's widgets change in place, such as an option added
through the related-object popup.

An object taken from a page is an address, read each time it is used, the way the browser
layer's own locators are:

* a field is the field of that name on the page (section 3.5);
* a row is the row at that position, so once the changelist is filtered or sorted it reads
  whichever record is there now;
* a cell is the cell of that column in its row.

`page.rows` and `page.fields` are a list and a dictionary of such addresses. Which rows and
fields they hold is fixed when they are read; reading them again picks up any the page has
gained or lost since.

Where the browser layer already has an answer, the package gives the same one and adds nothing
of its own:

* reading an address that finds nothing, such as a row held from before a filter left fewer
  rows, waits for the configured timeout and then fails, as a locator does;
* the package waits for the navigation its own actions cause; a test that navigates through a
  native handle waits for that navigation itself before it reads;
* the objects the package hands out compare by identity, as locators do.

`row.object` asks the database each time, so it is the object the row links to now, not the
one it linked to when the row was first read.

The one thing the browser layer cannot know is which admin page an object stands for, and the
package's own actions move the browser between pages. So a page object stands for its path and
for the kind of page the admin says it is: a changelist, a form, a delete confirmation, the
index. It stays usable for as long as the browser shows that page, whatever happened in
between. Once the browser shows another page, reading the page object, or anything taken from
it, fails at once and says where the browser is now, rather than waiting for the timeout
against a page it was never part of. A native handle is exempt: it is the browser layer's own
object and behaves as that layer decides.

The page an object stands for is the one the package last left the browser on for it. A page
that did not open where it was asked, such as one refused with a redirect to the login page,
stands for the page it landed on, so it can still say how it was refused.

`status_code`, and whether the page `works`, describe the last navigation the package itself
made on the page. One made through a native handle is not seen.

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
never a requirement for logging in. It returns the result of the submission (section 16), which
says whether the admin let the user in:

```python
result = admin_ui.login(user, password="secret")

assert result.success
assert result.redirected_to_index()
```

A refused login is no success, and its `result.page` is the login page the admin shows again,
which reads what the admin says about it:

```python
result = admin_ui.login(user, password="wrong")

assert not result.success
assert result.page.errors == [
    "Please enter the correct username and password for a staff account. "
    "Note that both fields may be case-sensitive."
]
assert result.page.field_errors == {}
assert admin_ui.index().denied
```

`errors` holds the notes the page shows above the form, in order, and is `[]` when it shows
none: why a login was refused, the same for a wrong password, an inactive user and a user who is
not staff; that the form has field errors; and that the user logged in now is not staff.
`field_errors` holds the errors the admin shows under each input that has any, by the input's
name, `username` or `password`. A username of only spaces is one, since Django strips it:

```python
page = admin_ui.login()
page.fill(username="   ", password="secret")
result = page.submit()

assert result.page.errors == ["Please correct the error below."]
assert result.page.field_errors == {"username": ["This field is required."]}
```

The message the browser itself shows for an empty input is not in either: the admin never sees
the form, and the browser shows the message only while the input stays empty. A test reads it
through `page.native`.

Both forms log out first, so the user given is the only one logged in. `login()` with no
arguments opens the login page instead, and logs nobody out: the admin serves it as it would to
whoever is logged in now. It sends a staff user on to the index, and shows a user who is not
staff the form with a note saying so.

The login page is filled and submitted in separate steps, so a test types whatever its subject
needs, empty and whitespace values included, and tries again on the same page after a refusal:

```python
page = admin_ui.login()
page.fill(username="alice", password="wrong")
result = page.submit()

assert not result.success

result.page.fill(password="secret")

assert result.page.submit().success
```

`fill` types each value given exactly as given and leaves an input it is not given as it is.
`username` names the form's input, whatever the user model calls the value. The browser itself
refuses to send the form while an input is empty; `submit` then returns at once with a result
that is no success, on the same page.

A submission from any other page that ends on the login page, such as a save after the session
ended, also has the login page as its `result.page`.

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

# 5. Permission Testing (done)

Permissions are tested through what the admin shows the current user, never through the
permission system directly. A test states what a user can see and do; the admin's own checks
decide the rest, and the package reports what they decided.

## 5.1 Pages (done)

A page the current user may not open must not report itself as working, and must say why:

```python
page = admin_ui.edit(product)    # done

assert not page.works            # done
assert page.denied               # done
```

The standard view, add, change and delete permissions are therefore tested by opening the
page each one guards:

```python
assert admin_ui.list(Product).works    # done
assert admin_ui.create(Product).denied  # done
```

---

## 5.2 Objects (done)

An admin may decide per object, through rules of its own or through an authentication backend
that answers per object. The page for that object reports what was decided, and a test never
needs to know which source produced it:

```python
assert admin_ui.delete(draft).works        # done
assert admin_ui.delete(published).denied   # done
```

---

## 5.3 Operations (done)

An admin may withhold an operation independently of the permission system, or gate an
operation of its own behind a permission the model never declared. Either way, what a user may
do shows up as what the page offers:

```python
page = admin_ui.edit(product)

assert not page.can_delete
assert page.has_action("_publish")
```

See section 16.1.

---

## 5.4 Models (done)

A user who may not see a model does not find it on the index:

```python
assert Product not in admin_ui.index().models
```

See section 24.

---

# 6. Admin Page Availability (done)

The package must provide abstractions for the admin index and for these four standard model
admin operations:

```python
admin_ui.index()           # done

admin_ui.list(Model)       # done
admin_ui.create(Model)     # done
admin_ui.edit(instance)    # done
admin_ui.delete(instance)  # done
```

Each returned page must make it easy to determine whether the page works.

Example:

```python
page = admin_ui.list(Product)    # done

assert page.works                # done
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

## 6.2 Page identity (done)

Pages expose the title and subtitle the admin renders for them:

```python
page = admin_ui.edit(product)

assert page.title == "Change product"
assert page.subtitle == "Widget"
```

---

## 6.3 Admin URLs (done)

Every admin page is addressable without being opened.

The package exposes a URL for each operation of this section:

```python
admin_ui.url.index()           # done

admin_ui.url.list(Model)       # done
admin_ui.url.create(Model)     # done
admin_ui.url.edit(instance)    # done
admin_ui.url.delete(instance)  # done
```

These are the values a test compares the path of a link against:

```python
assert page.rows[0]["customer"].links[0].href.path == admin_ui.url.edit(customer)    # done
```

URLs resolve through the admin site under test and its URL prefix. The package never assumes a
location, so a project that mounts its admin elsewhere gets correct URLs without changing its
tests. See section 28.2. (done)

A link read from a page keeps its `href` exactly as rendered, split into its parts, so a test
compares the whole against what it expects to see, or one part against the URL the package
produces for the same page. See section 9.8. (done)

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

## 6.5 Arbitrary admin pages (done)

Any admin URL can be opened, including views the package knows nothing about:

```python
page = admin_ui.open(reverse("admin:shop_product_import"))    # done

assert page.works                                             # done
assert page.title == "Import products"                        # done
```

Everything beyond that is reached through `page.native`.

Such a page guarantees what does not depend on knowing the page's shape:

* the access outcome of section 6.1 (done);
* the page identity of section 6.2 (done);
* the response status of section 6.4 (done);
* the operation messages of section 22 (done);
* a native handle (done).

It does not expose fields or rows. Their shape is unknowable for a page the package has never
seen, and guessing would be worse than declining.

---

# 7. List / Changelist Testing (done)

## 7.1 Column headers (done)

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

## 7.2 Column identity (done)

Columns are also addressable by the names the admin is configured with:

```python
assert page.columns == [
    "id",
    "first_name",
    "last_name",
    "email",
]
```

Both lists describe the same columns in the same order. Headers are what the user sees and
are read as data; names are how a test addresses a cell, as sections 3.5 and 9.7 describe.

---

## 7.3 Column objects (done)

One column is read as an object by its name:

```python
price = page.column("price")    # done

assert price.name == "price"    # done
assert price.label == "Price"   # done
assert price.sortable           # done
price.native                    # done
```

Its label is what `headers` lists for it, and its native handle is its header cell. A name that
isn't among `columns` raises `LookupError` listing the ones there are. The column is found by its
name each time it is used, so the same object keeps working after the page loads again, such as
after a search, and raises `LookupError` once the page no longer shows it. `columns` itself stays
a list of names, so it can be compared with a list as section 7.2 shows.

A changelist also lists the columns the user can sort by, by name, in the order shown:

```python
page = admin_ui.list(Product)

assert page.sortable_columns == ["name", "sku", "price"]    # done
assert "price_with_tax" not in page.sortable_columns         # done
```

This follows what the page shows rather than `ModelAdmin.sortable_by`, so it also follows
`get_sortable_by()`. A column of a method counts only when the method has an ordering, from
`@admin.display(ordering=...)` or `admin_order_field`. An empty changelist shows no table, so it
has no sortable columns. It is a list, like `columns` and `headers`, rather than a set like the
field groups of section 12, because it is read alongside them in the order shown.

A column also reads how it is sorted, as section 8.5 describes:

```python
assert price.sort_direction == "desc"                     # done
assert price.sort_direction == SortDirection.DESCENDING   # done
assert price.sort_priority == 1                           # done
```

`SortDirection` comes from `django_admin_kit.columns`. Its members are strings, so a direction
compares equal to `"asc"` or `"desc"` as well as to its member. Both are `None` for a column
that isn't sorted or can't be. Django shows a priority number only while two or more columns are
sorted, so a lone sorted column reads `1`.

---

# 8. Changelist Result Set (done)

## 8.1 Record count (done)

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

## 8.2 Empty changelist (done)

An empty changelist is an explicit, assertable state:

```python
page = admin_ui.list(Product)

assert page.works         # done
assert page.empty         # done
assert page.count == 0    # done
assert page.rows == []    # done
```

---

## 8.3 Search (done)

A changelist says whether it offers a search:

```python
assert admin_ui.list(Product).can_search      # done
assert not admin_ui.list(Feed).can_search     # done
```

The admin draws a search box only when it has search fields for the request, so this follows what
the page shows rather than `ModelAdmin.search_fields`.

`page.search` searches through that box. It returns nothing: the page stays the same object, and
the count, summary and rows read the results.

```python
page = admin_ui.list(Product)

page.search("Bolt")                           # done

assert page.count == 1                        # done
assert page.summary == "1 product"            # done
assert page.search_term == "Bolt"             # done
```

A search keeps any filters applied, and `page.search("")` clears the search. On a changelist
without a search box, nothing is clicked and `LookupError` says so. If the admin sends the browser
elsewhere, such as to the login page after the session ended, the page stands for where it landed
(section 3.9) and reports it as `denied` or `redirected`.

`page.search_term` is what the box shows at that moment, exactly as it shows it, and `""` on a
changelist without a box.

A changelist can also open with a term already applied:

```python
page = admin_ui.list(Product, search="Bolt")  # done

assert page.search_term == "Bolt"             # done
assert page.count == 1                        # done
```

The admin ignores a term when it has no search fields and shows every record, so on such a
changelist this raises `LookupError`, as `page.search` does. A page that did not open comes back as
usual, to say how it was refused.

---

## 8.4 Filters (done)

A changelist says whether it offers filters, and lists them by the field they filter, in the order
the sidebar shows them:

```python
page = admin_ui.list(Product)

assert page.can_filter                                      # done
assert not admin_ui.list(Feed).can_filter                   # done
assert list(page.filters) == ["is_active", "released_on"]   # done
```

This follows what the page shows rather than `ModelAdmin.list_filter`, so it also follows
`get_list_filter()`, and a filter the admin leaves out because it has nothing to offer isn't there.
`page.filters` is a read-only mapping, and a field without filters raises `KeyError` listing the
fields there are.

A filter is addressed by its field, never by its title, which repeats and is translated. The page
doesn't say which `list_filter` entry a filter came from, so the field comes from the parameters
its links send: a trailing lookup and a relation's target are removed, so `category__id__exact`
names `category`. A filter of the project's own is named after its `parameter_name`. When a
filter's parameters name different fields, the part they share up to a `__` is used, or else the
first of them in sorted order.

Each field has a group of filters, usually one. Two filters on one field, such as a date filter and
an `EmptyFieldListFilter` on `released_on`, share a group, in the order shown, and are reached by
index:

```python
dates = page.filters["released_on"]

assert len(dates) == 2                                      # done
dates[1].native                                             # done
```

An index depends on the order of `list_filter`. A filter drawn with inputs instead of links, as
range filters often are, has no choices to pick, so it isn't listed; a test fills it through
`page.native`.

A filter reads its choices and the one the page marks selected, as labels:

```python
active = page.filters["is_active"]

assert active.choices == ["All", "Yes", "No"]               # done
assert active.selected == "All"                             # done
```

The labels are read as the page shows them, so with Django's counts on they read "Yes (3)". A
date filter's first choice is "Any date". `selected` is `None` when the page marks no choice, as
Django does for a date filter while another filter on the same field is applied.

A group of one filter reads as that filter. A group of several reads a list, one item per filter in
the order shown:

```python
assert dates.choices == [                                   # done
    ["Any date", "Today", "Past 7 days", "This month", "This year", "No date", "Has date"],
    ["All", "Empty", "Not empty"],
]
assert dates.selected == ["Any date", "All"]                # done
```

A filter applies a choice by its label. It returns nothing: the page stays the same object, and
the count, summary and rows read the results.

```python
active.apply("No")                                          # done

assert active.selected == "No"                              # done
assert page.count == 0                                      # done
```

`apply` clicks the link the admin renders, so Django decides what the click keeps: a search and the
other filters' values. A label also matches with Django's count after it, so `apply("Yes")` applies
"Yes (3)". A label the filter doesn't offer, or offers more than once, raises `LookupError`, and
nothing is clicked. A filter the user collapsed is opened first. If the admin sends the browser
elsewhere, such as to the login page after the session ended, the page stands for where it landed
(section 3.9) and reports it as `denied` or `redirected`.

On a group, `apply` uses whichever filter offers the label. A label several of them offer, such as
"All", raises `LookupError` naming them by index, and is applied through one of them:

```python
dates[1].apply("All")                                       # done
```

Two filters on one field don't always agree about the URL. The date filter's links leave out every
parameter of its field, so "Empty" then "Has date" drops "Empty", while "Has date" then "Empty"
keeps both, and the date filter then marks no choice. The package reports what Django does:

```python
dates.apply("Empty")
dates.apply("Has date")

assert dates.selected == ["Has date", "All"]                # done
```

Filters are cleared without a label, so in any language:

```python
page.filters.clear()                                        # done
page.filters["released_on"].clear()                         # done
dates[1].clear()                                            # done
```

`page.filters.clear()` clicks the admin's "Clear all filters", which keeps a search and the
ordering. A filter's `clear()` clicks the choice that removes its parameters, "All" or "Any date"
as a rule, and a group's clears each of its filters in order. Each does nothing when nothing it
would clear is applied, and the page isn't loaded again. A changelist without filters raises
`LookupError`, and so does a filter applied without a choice that clears it, such as one of the
project's own without "All".

---

## 8.5 Sorting (done)

Django sorts a changelist by several columns at once. Clicking a header makes that column the
first sort key and keeps the columns sorted before behind it, so a changelist sorted by name and
then clicked on "Price" is sorted by price and then by name. A sorted header has an arrow, which
flips its direction and keeps its place, and a link that removes it from the sort.

A changelist lists the columns it shows sorted, in priority order, with `-` in front of a
descending one, the way `ModelAdmin.ordering` writes them:

```python
page = admin_ui.list(Product)

assert page.sorted_columns == ["name"]                # done
```

These are the marks Django puts on the headers, as `sort_direction` and `sort_priority` of
section 7.3 are. While the URL asks for no sort, Django marks the columns of the admin's default
ordering it can match to a column: a field that isn't a column and an expression such as
`Lower("name")` are left out, and of two columns on one field only the first is marked. It never
marks the `-pk` it adds last to break ties. So these follow the headers, and the rows show the
real order. `sorted_columns` is `[]` when no column is marked, and on an empty changelist, which
shows no table.

A column changes how it is sorted with three methods, one for each thing a user does on its
header:

```python
price = page.column("price")

price.make_primary_sort("desc")                       # done
assert page.sorted_columns == ["-price", "name"]      # done

price.set_sort_direction("asc")                       # done
assert page.sorted_columns == ["price", "name"]       # done

price.remove_from_sort()                              # done
assert page.sorted_columns == ["name"]                # done
```

`make_primary_sort` makes the column the first sort key, ascending unless it is given `"desc"`,
and keeps the columns sorted before after it in their order. It clicks the header, then the
arrow when the click left the column in the other direction, since a click on a sorted header
flips it. `set_sort_direction` keeps the column's place and clicks the arrow when its direction
differs. `remove_from_sort` clicks the link that removes the column, which the admin shows only
while the pointer is over the header, so the pointer is moved there first. A direction is a
`SortDirection` or its string; anything else raises `ValueError`.

Each returns nothing: the page stays the same object, and the count, the rows and the sort read
the results. Each does nothing, and the page isn't loaded again, when the column is already
sorted as asked: first in that direction, in that direction, or not sorted at all. A column the
user can't sort by raises `LookupError`, and so does `set_sort_direction` on a column that isn't
sorted, which has no place to keep: Django adds a column to the sort only as the first one, so
the error points to `make_primary_sort`. Nothing is clicked in either case. If the admin sends
the browser elsewhere, such as to the login page after the session ended, the page stands for
where it landed (section 3.9), reports it as `denied` or `redirected`, and nothing more is
clicked.

A test that wants the changelist sorted one way, whatever it was sorted by before, gives the
whole sort to `page.sort`, in the format `sorted_columns` reads:

```python
page.sort("-price", "name")                           # done
assert page.sorted_columns == ["-price", "name"]      # done

page.sort("sku")                                      # done
assert page.sorted_columns == ["sku"]                 # done

saved = page.sorted_columns                           # done
page.sort()                                           # done
assert page.sorted_columns == []                      # done
page.sort(*saved)                                     # done
```

The two differ in what they keep. `make_primary_sort` changes one column and keeps the others
sorted after it, as a click on a header does. `page.sort` sorts by exactly the columns given, so
a column sorted before and left out is no longer sorted, and `page.sort()` sorts by none. To add
a column in front of the current sort, a test uses `make_primary_sort`.

`page.sort` works through the same controls. It removes the sorted columns it leaves out. The
columns given that the headers already end with, in that order, keep their place, and the arrow
flips any of them sorted the other way. The rest are made primary from the last to the first,
since each one made primary goes in front. From a changelist sorted by SKU, `page.sort("-price",
"name")` removes the SKU, clicks the header of the name, then the header and the arrow of the
price. From one sorted by name and price, `page.sort("name", "-price")` clicks only the arrow of
the price. When the headers already show the sort asked for, nothing is clicked and the page
isn't loaded again.

Every name is checked before the first click. A name that isn't a column, `""`, `"-"` and
`"--price"` included, raises `LookupError` as `page.column` does. A column the user can't sort by
raises `LookupError` listing the ones they can, and a column given twice, in either direction,
raises `ValueError`. A refused click is reported as for the column's methods, and nothing more
is clicked. The error of `set_sort_direction` on a column that isn't sorted points to
`page.sort` too.

The links come from Django, which keeps the rest of the URL: sorting keeps a search and the
filters applied, and a search, a filter and "Clear all filters" keep the sort. Once the last
column is removed, or `page.sort()` sorts by none, the URL asks for an empty sort, and the
headers mark no column. Django 5.2
and later then order the records by the admin's default ordering again; earlier versions order
them by their primary key alone, newest first.

---

## 8.6 Pagination (done)

Django shows `list_per_page` records a page, 100 unless the admin says otherwise. A changelist
reads which page it shows, counting from 1, and how many pages there are:

```python
page = admin_ui.list(Product)

assert page.page_number == 1                          # done
assert page.page_count == 3                           # done
```

Both are read from the paginator, never from the admin's `list_per_page`. `page_number` is the
page the paginator marks current. `page_count` is the highest number it shows: with more than 10
pages Django leaves out the numbers far from the current page, but always shows the last one. A
changelist that fits on one page shows no page links, so it is page 1 of 1, and so is an empty
one. `count` is the number of records across every page, and `rows` are the rows of the page
shown.

`page.go_to_page` shows another page by its number. It returns nothing: the page stays the same
object, and the rows read the new page.

```python
page.go_to_page(3)                                    # done

assert page.page_number == 3                          # done
```

When the paginator shows the number, its link is clicked. From page 1 of 20 it shows
`1 2 3 4 … 19 20`, so page 10 has no link. For such a page, the address of a link Django drew is
opened with only its page number changed, so it carries the search, filters and sort as the
link does. Either way the page loads once, and going to the page shown loads nothing.

A page link keeps a search, the filters and the sort. A search, a filter and a sort go back to
page 1, because Django's links for them leave out the page number.

A number that isn't an `int` raises `TypeError`, `True` and `False` included, since `True`
taken as page 1 would hide a mistake. A number outside 1 to `page_count` raises `LookupError`
saying how many pages there are. Both are raised before anything is clicked. If the admin sends
the browser elsewhere, such as to the login page after the session ended, the page stands for
where it landed (section 3.9) and reports it as `denied` or `redirected`.

A test that reads every page goes through them in turn:

```python
names = []
for number in range(1, page.page_count + 1):          # done
    page.go_to_page(number)                           # done
    names += [row["name"].value for row in page.rows] # done
```

A changelist says whether it offers "Show all", shows all of its records on one page, and says
whether it shows them all:

```python
assert page.can_show_all                              # done

page.show_all()                                       # done

assert page.shows_all                                 # done
assert len(page.rows) == page.count                   # done
```

Django draws "Show all" while the records span several pages and number no more than the admin's
`list_max_show_all`, 200 unless it says otherwise. `show_all` clicks it and returns nothing, and
the same page then reads all the rows. It does nothing when the page already shows all, and the
page isn't loaded again. A changelist that doesn't offer it, because it fits on one page or has
too many records, raises `LookupError`, and nothing is clicked. A refused click is reported as
for `go_to_page`.

While it shows all, the paginator draws no page links, so the changelist is page 1 of 1, and
`go_to_page` with any other number raises `LookupError` saying so. A search, a filter and a sort
keep showing all, and Django draws no control that goes back to the pages.

`shows_all` is the one reader that goes by the address rather than the markup. A changelist
showing all looks like one that fits on one page, so `shows_all` is true when the address asks for
all records and the paginator draws no page links, which it would if there were too many to show.

---

## 8.7 Actions (done)

A changelist lists the actions it offers in its action bar, by name, in the order the bar lists
them. `page.actions` is a read-only mapping, as `page.filters` is, and each action reads its
name, its label and its `<option>` as `native`:

```python
page = admin_ui.list(Product)

assert list(page.actions) == ["delete_selected", "mark_inactive"]           # done
assert page.actions["mark_inactive"].label == "Mark selected products as inactive"  # done
```

An action is addressed by the name the admin registers it under, and its label, the description
the bar shows, is read as data (section 3.5). The bar's blank `---------` option is no action.
The actions are read from the page, never from `ModelAdmin.get_actions`, so they follow the
user's permissions: Django leaves out an action the user may not run, and draws no bar when
none is left. It draws none either while it counts the records and finds none. Without a bar,
`page.actions` is empty. An admin that draws a bar above the table and one below lists the same
actions in both, and the first is read.

A key that names no action raises `KeyError` listing the names there are, or saying the
changelist offers none. A label raises it too, and so does `""`. The mapping and each action
read the page again whenever they are used (section 3.9), so an action held across a search
still works, and one the page no longer offers raises `LookupError`.

An action runs on the rows selected. A row is selected through its checkbox, and every row on
the page at once through the checkbox over them:

```python
page.rows[0].select()                                 # done
page.rows[2].select()                                 # done

assert [row.selected for row in page.rows] == [True, False, True]  # done

page.rows[0].deselect()                               # done
page.select_all()                                     # done
page.deselect_all()                                   # done
```

None of them loads a page: the selection lives in the browser until an action is run, as a
user's does. Each does nothing when the rows are already as asked. They check and uncheck the
boxes as a user does, so the admin's script keeps the box over the rows and the counter in step.
A row is addressed by its position (section 3.5), so after a search or a sort the same row may
be another record, and the page loaded again starts with nothing selected.

A changelist that offers no actions draws no checkboxes. Its rows read as not selected, and
`select`, `deselect`, `select_all` and `deselect_all` raise `LookupError` saying it offers no
actions. A row held after the browser moved on raises `LookupError`, as reading its cells does.
There is no `page.select(*indexes)`, which would be a second way to write
`page.rows[0].select()`.

An action can run on every record the changelist lists, across its pages:

```python
page.select_across_pages()                            # done

assert page.selects_across_pages                      # done
```

`select_across_pages` selects every row on the page, then clicks the admin's "Select all N",
which loads nothing, as selecting a row doesn't. An action then runs on every record the search
and the filters let through. Deselecting a row, or every row, selects only the rows checked
again, as the admin's script does for a user. Django offers the link only while the records span
several pages and the admin shows its selection counter (`actions_selection_counter`), so
otherwise `select_across_pages` raises `LookupError`, and nothing is clicked. The package finds
out from the page, which carries the link, hidden, whenever Django offers it. It does nothing
when the page already selects across pages, and `selects_across_pages` is `False` on a
changelist that offers no actions.

`action.run()` chooses the action in the action bar, clicks the bar's button, and returns the
page the browser shows after it:

```python
page.rows[0].select()                                 # done
page.rows[2].select()                                 # done

landed = page.actions["mark_inactive"].run()          # done

assert landed is page                                 # done
assert page.messages == [("success", "2 products were marked as inactive.")]  # done
```

When the admin comes back to the changelist, as it does after an action that returns no
response, `run` returns this same changelist object, which then reads the page loaded again
with the search and filters it had and nothing selected. Otherwise it returns a new page object
for wherever the action led, the way a submission's `result.page` is built (section 16.4): an
`EditPage` for the change page an action redirects to, or a plain `AdminPage` for a page of the
project's own. Its type is `AdminPage`, since an action can lead anywhere, and a test narrows
it with `isinstance`.

`run` returns the page rather than a `SubmissionResult`, whose `success` says whether the admin
redirected: Django redirects after refusing to run an action, so that would mean nothing here.

An action runs with nothing selected too, as a user can run one. Django then changes nothing
and comes back to the changelist with its warning, which `page.messages` reads:

```python
landed = page.actions["mark_inactive"].run()          # done

assert landed is page                                 # done
assert page.messages == [                             # done
    ("warning", "Items must be selected in order to perform actions on them. "
                "No items have been changed."),
]
```

An action the changelist no longer offers raises `LookupError`, and nothing is clicked. With two
action bars, the action is chosen in the first and that bar's button is clicked. After the
session ended, the admin sends the browser to the login page, and `run` returns a `LoginPage`
that reads as `denied`.

The admin's own "Delete selected" leads to a confirmation, a `DeletePage`, read and confirmed
as the page that deletes one object is (sections 23.4 and 23.5):

```python
page.select_all()

confirmation = page.actions["delete_selected"].run()  # done

assert isinstance(confirmation, DeletePage)           # done
assert confirmation.deletion_counts == {"Products": 3}  # done
assert confirmation.confirm_deleting().redirected_to_list(Product)  # done
```

Django draws both confirmations alike and answers the action with this one at the changelist's
own URL, without a redirect, so its `destination` is the changelist's. `deletions` lists
each selected object in turn, followed by what it takes with it. When objects protect the
selection, or it would take with it objects the user may not delete, the page offers no
confirmation and lists them as `blockers`, as the single page does. Confirming deletes the
objects and leads back to the changelist, which says how many it deleted.

---

# 9. Changelist Row Matching (done)

One of the main 1.0.0 features is concise verification of rows shown on a changelist.

`contains` takes one row pattern and passes when at least one row of the changelist matches
it. It returns `True`, and when no row matches it raises `AssertionError` with the expected
pattern and the rows actually shown, as section 30 describes:

```python
assert page.contains((1, "Jane", "Doe", "", ANY, some_callable))    # done
```

A row pattern is a tuple or a list of cell patterns, one per column in the order shown; a
dictionary of cell patterns by column, as in section 9.7; or `ANY_ROW`. A cell pattern is a
value, a link, a list or tuple of links, `ANY` or a callable (section 9.8). `contains` takes
exactly one row pattern; a test that expects several rows calls it once per row.

`match` takes a list or a tuple of row patterns and describes the whole changelist: there
are exactly as many rows as patterns, and the pattern at each position matches the row at
that position.

```python
assert page.match([    # done
    (1, "Jane", "Doe", "", ANY, some_callable),
    ANY_ROW,
    {"first_name": "John"},
])
```

`ANY_ROW` then matches whatever row holds its position; it is there to keep the count and
the positions of the others. A changelist of one row is `match([row])`; `match` always takes
the list, so that a row of cell patterns is never mistaken for a list of rows.

## 9.1 Matcher vocabulary (done)

Expected values are matched using four things, and nothing else:

* literal values, compared for equality; (done)
* links, as `Link` objects or `(text, href)` pairs, compared against the links a cell
  renders; (done)
* the sentinels `ANY` and `ANY_ROW`; (done)
* callables. (done)

No string value carries matcher meaning. A string in an expected row is always a literal value.

---

## 9.2 Literal values (done)

Literal values require equality.

```python
("Jane", "Doe")
```

means that the corresponding cells must contain exactly those expected normalized values.

---

## 9.3 Empty value (done)

An explicitly provided empty value:

```python
""
```

is a literal like any other: the corresponding cell is expected to show nothing. The text the
admin shows for a value it has none of, such as `"-"`, is text and is matched as text; see
section 9.8.

It is distinct from `ANY`.

---

## 9.4 Any-value matcher (done)

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

## 9.5 Callable matcher (done)

A callable may be supplied for a cell.

Example:

```python
def valid_email(row, cell):
    return cell.value.endswith("@example.com")


assert page.contains((1, "Jane", "Doe", valid_email))    # done
```

The callable signature is:

```python
matcher(row, cell)
```

It returns a truthy value for a successful match.

`cell` is the cell being matched, as section 9.8 describes it: `cell.value` is its normalized
meaning, `cell.links` its links where it renders any, and `cell.native` the
element itself. A cell the admin renders as something other than text, such as an icon, an
image or a button, is therefore still matchable: by its normalized value where the package
knows the rendering, and through `cell.native` where it does not.

`row` is the row the cell belongs to, as section 9.7 describes it: `row["email"]` is one cell
by column and `row[3]` one by position,
`row.index` is its 0-based position, `row.native` is the element itself, and `row.object` is
the model instance behind it, where the changelist links to one.

---

## 9.6 Ignore entire row contents (done)

`ANY_ROW` is a row pattern that any row matches:

```python
assert page.contains(ANY_ROW)    # done
```

This passes when the changelist has at least one row. It claims no more than `not page.empty`
does; on its own it exists so that `ANY_ROW` is a valid pattern wherever a row pattern is
accepted. In `match` it holds a row's position:

```python
assert page.match([    # done
    (1, "Jane", "Doe", ""),
    ANY_ROW,
])
```

`ANY_ROW` is the only spelling for it.

---

## 9.7 Cell addressing by column (done)

`page.rows` is the list of rows the changelist shows, in the order shown. A row is addressed
by position in it, and a cell by the configured name of its column or by position in the row,
as described in section 3.5. What that gives is the cell, whose normalized value is `value`:

```python
assert page.rows[0]["first_name"].value == "Jane"    # done
assert page.rows[0]["email"].value == ""             # done
assert page.rows[0][1].value == "Jane"               # done
```

An expected row may be expressed the same way, in which case unlisted columns are not
constrained:

```python
assert page.contains({    # done
    "first_name": "Jane",
    "last_name": "Doe",
    "email": lambda row, cell: cell.value.endswith("@example.com"),
    "status": ANY,
})
```

This makes it possible to assert a few meaningful columns without enumerating a wide changelist.
The keys are configured column names, as above. The values are cell patterns: literals, links,
`ANY` and callables, exactly as in a tuple. `ANY` on a listed column says only that the column is
there, which a dictionary otherwise leaves unsaid.

---

## 9.8 Normalized cell values (done)

Cell values follow section 3.4.

Booleans normalize to booleans:

```python
assert page.rows[0]["is_active"].value is True    # done
```

A value the admin has none of reads as the text it shows in its place, whether the site's
default or one the project configured:

```python
cell = page.rows[0]["released_on"]

assert cell.value == "(none)"    # done
assert cell.text == "(none)"     # done
```

`text` is what the document shows in any cell, before normalization: the text of a link,
nothing for an icon. Out of the box `value` differs from it only where the admin drew
something other than text.

A cell the admin renders as a link keeps its text as its value and exposes the link
separately as a `Link`, with the text and the `href` exactly as rendered; a cell may carry
several, so `links` is always a list, empty for a cell with none. A `Link` compares equal to
a `(text, href)` pair, so a test writes the pair it expects to see:

```python
cell = page.rows[0]["customer"]

assert cell.value == "Jane Doe"                                          # done
assert cell.links == [("Jane Doe", "/admin/shop/customer/7/change/")]    # done

assert page.rows[0]["attachments"].links == [    # done
    ("first.pdf", "/media/first.pdf"),
    ("second.pdf", "/media/second.pdf"),
]
```

`href` is the standard split URL (`urllib.parse.SplitResult`), so its parts are there by
name for a test that wants one of them, such as the path compared against the admin URLs of
section 6.3, or the query string the admin adds to keep a filter across a round trip:

```python
link = cell.links[0]

assert link.text == "Jane Doe"                              # done
assert link.href.path == admin_ui.url.edit(customer)        # done
assert "_changelist_filters" in link.href.query             # done
```

In a pair, `href` may be given as a string or as a split URL; a string is split before
comparing.

Whatever the admin renders in a cell, its normalized value is what the user reads there: text
for text, a boolean for a boolean icon, the text of a link. A rendering the package does not
know normalizes to the cell's text, and `cell.native` is there for the rest, as section 3.6
describes. Each of these rules is a normalizer of section 28.3.

A row pattern therefore matches what is read, and never a link. A row whose first column
links to the change page and whose last is a boolean icon matches plain data:

```python
assert page.contains(("Widget", "SKU-1", "10.00", True))    # done
```

Where a link matters, a link in place of a cell's value matches a cell that renders exactly
that one link, and a list or tuple of links a cell that renders exactly those, in that order.
A link is written as a `(text, href)` pair or as a `Link`, the same two spellings that compare
equal to `cell.links`. A cell pattern matches when it equals the cell's value or the cell's
links, so a project whose own rule (section 28.3) puts links into `value` matches them the
same way:

```python
assert page.contains((("Widget", "/admin/shop/product/1/change/"), "SKU-1", "10.00", True))    # done
assert page.contains({"attachments": [("first.pdf", "/media/first.pdf"), Link("second.pdf", "/media/second.pdf")]})    # done
```

A link matches the rendered `href` whole; a test on a page where the admin has added to it,
such as a filtered changelist, matches the part it cares about through a callable:

```python
assert page.contains((lambda row, cell: cell.links[0].href.path == admin_ui.url.edit(product), "SKU-1", "10.00", True))    # done
```

---

## 9.9 Row ordering (done)

`contains` verifies existence: one row matches the pattern, and it says nothing about the
rows left over.

`match` verifies the complete changelist in order: as many rows as patterns, each at its
position.

```python
assert page.match([    # done
    (1, "Jane", "Doe", ""),
    (2, "John", "Doe", "john@example.com"),
])
```

A complete changelist in any order is one `contains` per row together with the count:

```python
for row in rows:
    assert page.contains(row)    # done
assert page.count == len(rows)   # done
```

The sentinels and callables of section 9.1 apply in both methods alike.

---

# 10. Create Page Fields (done)

The package must expose the fields present on the create page.

Example:

```python
page = admin_ui.create(Product)

assert set(page.fields) == {    # done
    "name",
    "price",
    "description",
    "enabled",
}
```

`page.fields` is a mapping from field name to field, in the order the admin presents them, so
membership and subset checks are plain Python: (done)

```python
assert "name" in page.fields                     # done
assert {"name", "price"} <= set(page.fields)     # done
```

A field is addressed by name, as section 3.5 says:

```python
field = page.fields["name"]    # done
```

Asking for a field the form does not have raises `KeyError`, naming it and listing the fields
the form does have, so the failure reads at a glance. (done)

A field the admin renders hidden, through a `HiddenInput` widget, is not shown to the user and
is not in `page.fields`. The browser posts it with the form as it is, and `page.native` reaches
it when a test has to. (done)

---

# 11. Edit Page Fields (done)

The edit page must expose the same field-inspection API:

```python
page = admin_ui.edit(product)

assert "name" in page.fields             # done
assert page.fields["name"].required      # done
```

Fields expose their currently rendered value:

```python
assert page.fields["name"].value == "Widget"    # done
```

---

# 12. Required and Optional Fields (done)

The package must distinguish required and non-required admin form fields.

Example:

```python
page = admin_ui.create(Product)

assert page.fields["name"].required                 # done
assert not page.fields["description"].required      # done
```

Convenience collections should be exposed:

```python
assert page.required_fields == {    # done
    "name",
    "price",
}

assert page.optional_fields == {    # done
    "description",
    "enabled",
}
```

The result must reflect the actual admin form, including custom `ModelForm` behavior, rather
than only the model field definition. (done)

A field the user may only read is in neither collection: nothing is there to fill. (done)

The fields the user may only read and the ones with a control to fill are named the same way:

```python
assert page.readonly_fields == set()    # done

assert page.editable_fields == {    # done
    "name",
    "price",
    "description",
    "enabled",
}
```

Both follow what the admin renders rather than `ModelAdmin.readonly_fields`, so a field the
admin's `get_readonly_fields` locks for one object is read-only on that object's page only, and
a user who may only view gets every field as read-only. Every field is in exactly one of them,
and the editable fields are the required and the optional ones together. (done)

---

# 13. Field Metadata (done)

Beyond existence and requiredness, a field exposes what the admin says about it.

## 13.1 Labels (done)

```python
assert page.fields["first_name"].label == "First name"    # done
```

Fields are addressed by name; the label is data, not an address. The suffix the form puts
after every label, `:` in English, is not part of it, whatever the page's language makes of
it. (done)

---

## 13.2 Initial values (done)

The create page exposes the values the admin starts with:

```python
page = admin_ui.create(Product)

assert page.fields["enabled"].value is True     # done
assert page.fields["quantity"].value == "1"     # done
```

A split date-time, which the admin draws as a date input and a time input, reads as the two
texts they hold, and is filled from a `datetime`, from a `(date, time)` pair, each half a date
or time, text or `None`, or from `None`, which empties both. Dates and times are typed in ISO
format, and an aware `datetime` in the current time zone:

```python
page.fields["published_at"].fill(datetime.datetime(2026, 1, 15, 9, 30))    # done
assert page.fields["published_at"].value == ("2026-01-15", "09:30:00")     # done

page.fields["published_at"].fill(("2026-11-03", "11:25:48"))               # done
```

A file input reads as a `FormFile`, the file it holds, or `None` when it holds none. A
`FormFile` has the file's `name` and its `href`, split as a link's is. A stored file is the one
the admin names after "Currently", with the link it draws to it. A file the user chose has the
name the browser gives it, without its folders, and no `href`, since it is not uploaded yet. A
file compares equal to a `(name, href)` pair, and is filled from a path, as text or a path
object; a path that is no file raises `FileNotFoundError`. `None` or `""` empties the field: it
drops a chosen file and checks "Clear" for a stored one, after which the field reads as `None`,
what the submission sends. The admin draws no "Clear" for a required field, so emptying one that
holds a stored file raises `ValueError`. A Django `File`, such as the `FieldFile` a model
instance holds, fills the field with its content, uploaded under its name without folders and
read through the file itself, so a file in any storage is uploaded; a `FieldFile` with no file
empties the field, and a `File` without a name raises `ValueError`. An image field has the same
input and reads the same:

```python
page = admin_ui.edit(manual)
assert page.fields["file"].value == ("manuals/a.pdf", "/media/manuals/a.pdf")    # done

page.fields["file"].fill("tests/data/b.pdf")                                     # done
assert page.fields["file"].value == ("b.pdf", None)                              # done

page.fields["cover"].fill(None)                                                  # done
assert page.fields["cover"].value is None                                        # done
```

The input the admin draws for a field named in `raw_id_fields` reads as the text it holds, the
ids the form posts, such as `"7"`, or `"1,2"` for a many-to-many field, and `""` while empty. It
is filled with an id: text as is, an `int`, a model instance written as its pk, or a
`FieldChoice` as its value. `None` and `""` empty it. The input for a many-to-many field also
takes a list of those, joined with `,` as the admin joins them, and the one for a foreign key
refuses a list with `TypeError`. The name the admin shows next to the input comes from the
server and describes the stored value until the form is sent again, so it is not part of the
value:

```python
page.fields["replacement"].fill(bolt)                    # done
assert page.fields["replacement"].value == "7"           # done

page.fields["spares"].fill([bolt, nut])                  # done
assert page.fields["spares"].value == "7,8"              # done
```

---

## 13.3 Choices (done)

A field with a fixed set of options exposes them as value and label pairs, including the blank
option where the admin renders one; a field without options exposes `[]`:

```python
field = page.fields["category"]

assert field.choices == [    # done
    ("", "---------"),
    ("1", "Tools"),
    ("2", "Toys"),
]
```

Subset checks should be natural:

```python
assert ("2", "Toys") in field.choices    # done
```

Each option is a `FieldChoice` with a `value`, what the form posts, and a `label`, what the user
reads. The `value` of a field with options is the `FieldChoice` chosen. A choice compares equal
to another choice and to a `(value, label)` pair written as a tuple or a list, never to a bare
string, so a test says which part it means: (done)

```python
field = page.fields["category"]

assert field.value == ("2", "Toys")     # done
assert field.value.value == "2"         # done
assert field.value.label == "Toys"      # done
assert field.value in field.choices     # done
```

A multiple select, which the admin draws for a many-to-many field, reads as the list of the
choices made, in the order offered, and `[]` when none is. It is filled with a list or another
iterable of values, each written as for a select, and the choices become exactly those; `None`
and `[]` clear them. A lone value is refused with `TypeError`, so it is written as `[value]`:

```python
field = page.fields["categories"]

field.fill([toys, tools])
assert field.value == [("1", "Tools"), ("2", "Toys")]    # done
field.fill([])
assert field.value == []                                 # done
```

The two lists the admin's script draws for a field named in `filter_horizontal` or
`filter_vertical`, the options available and the ones chosen, are read and filled as a multiple
select is, with the value read from the chosen list, as it shows them. `fill` moves every chosen
option out and then each value given in, so the field reads the values in the order given; a
value given twice is chosen once, and nothing moves when the chosen list already holds the
values in that order. `choices` are the available options, then the chosen ones, as shown. The
admin sorts neither list, and a moved option goes to the end of the other one, so the order of
`choices` follows the moves while the options stay the same, and a test that doesn't care
about the order compares `set(field.choices)`:

```python
field = page.fields["categories"]

field.fill([toys, garden])
assert field.value == [("3", "Toys"), ("1", "Garden")]                   # done
assert field.choices == [("2", "Tools"), ("3", "Toys"), ("1", "Garden")]  # done
```

The box the admin draws for a field named in `autocomplete_fields` is read and filled as a
select is, or as a multiple select for a many-to-many field. It holds only the options chosen,
and the others come from the admin's autocomplete view as the user types, so `choices` are every
option that view offers for an empty search, page by page, after the blank option of an optional
box, whose label is empty where a select's reads `---------`. `fill` takes any of those choices,
whether the box held an option for it or not, and a many-to-many box reads the values in the
order given:

```python
field = page.fields["lead"]

assert field.value == ("", "")                                   # done
assert field.choices == [("", ""), ("1", "Bolt"), ("2", "Nut")]  # done
field.fill(nut)
assert field.value == ("2", "Nut")                               # done
```

Radio buttons, which the admin draws for a field named in `radio_fields`, are read, filled and
listed as a select is. Their value is `None` while none is checked, and `None` fills the blank
option where the admin draws one, labeled "None":

```python
field = page.fields["section"]

field.fill(toys)
assert field.value == ("2", "Toys")                                      # done
assert field.choices == [("", "None"), ("1", "Tools"), ("2", "Toys")]    # done
```

---

## 13.4 Rendered-only fields (done)

A field is either editable or rendered only.

A rendered-only field has no input to fill, but still has a value:

```python
field = page.fields["created_at"]

assert not field.editable                 # done
assert field.value == "1 January 2026"    # done
```

Where the admin renders such a field as a link, the link is available as on a changelist cell,
section 9.8:

```python
assert page.fields["owner"].links == [("Jane Doe", admin_ui.url.edit(owner))]    # done
```

Rendered-only fields are never populated by section 14 and never appear in
`page.required_fields` (done). Filling one is not silently skipped but reported, since there
is no control to put a value in:

```python
page.fields["created_at"].fill("2026-01-15")    # LookupError (done)
```

---

## 13.5 Field order (done)

`page.fields` is ordered as the admin presents the fields, so their order is read from it:

```python
assert list(page.fields) == [    # done
    "name",
    "price",
    "description",
    "enabled",
]
```

Section 13.7 reads the fieldsets the fields are drawn in. (done)

---

## 13.6 Help text (done)

A field exposes the help the admin shows with it, as the user reads it, without its markup, and
`""` for a field without any:

```python
page = admin_ui.create(Product)

assert page.fields["sku"].help_text == "The code printed on the label."    # done
assert page.fields["name"].help_text == ""                                  # done
```

A rendered-only field has help text too: the admin shows the help of the model field behind it,
so a user who may only view reads the same help as one who may edit. (done)

The links a help text may hold are reached through `field.native`. The note the admin's
date-time script adds when the browser and the server disagree on the time zone is not part of
the help text. (done)

---

## 13.7 Fieldsets (done)

`page.fieldsets` lists the fieldsets the admin draws the form's fields in, in order. Each one has
its name, its description and its fields:

```python
page = admin_ui.create(Feed)

assert [fieldset.name for fieldset in page.fieldsets] == [None, "Schedule", "Appearance"]    # done

schedule = page.fieldsets[1]
assert schedule.description == "When the feed last ran, and the time it runs each day."     # done
assert list(schedule.fields) == ["refreshed_at", "refresh_time"]                            # done
```

A fieldset without a name has `None` as its name, and one without a description has `None` as
its description, as Django has them. The name and the description are read as the user reads
them, without their markup. (done)

`fieldset.fields` is a mapping like `page.fields`: the fieldset's own fields by name, in order,
leaving out the hidden ones. A field is read and filled through it as through `page.fields`,
and a name the fieldset does not have raises `KeyError` listing the fields it has. Together the
fieldsets hold every field of `page.fields`, in the same order. (done)

```python
schedule.fields["refresh_time"].fill("06:00:00")    # done
```

A form whose admin sets no `fieldsets` has one fieldset, without a name, that holds every
field. The fieldsets of inlines are not part of it. (done)

A fieldset the admin lets the user collapse is `collapsible`, and `collapsed` says whether its
fields are hidden under its name right now. Both follow the page: the admin draws a fieldset
that shows errors open and without its toggle, so on that page it is neither. (done)

```python
assert schedule.collapsible    # done
assert schedule.collapsed      # done
```

The fields of a collapsed fieldset are read as any other field is. Filling one opens the
fieldset first, through its toggle, as the user has to, so the fieldset is open afterward. A
test that checks the toggle itself opens and closes the fieldset with `open()` and `close()`.
Each does nothing when the fieldset is already that way, and both raise `LookupError` on a
fieldset that is not collapsible. (done)

```python
schedule.fields["refresh_time"].fill("06:00:00")    # done
assert not schedule.collapsed                       # done

schedule.close()                                    # done
assert schedule.collapsed                           # done
```

---

## 13.8 Related objects

The "+" the admin draws next to a field of related objects opens the page that adds one in a
popup, and the pencil opens the page that changes the one chosen. `field.add_related()` and
`field.change_related()` click them and return that page, a create page and an edit page like any
other, whose `native` is the popup window. (done)

Once the admin accepts a popup's save it closes the popup and updates the field, so the result is
a success, and its page is the one the popup was opened from. A rejected form stays in the popup,
and the result's page is the popup's. Reading a popup's page once the popup is closed raises
`LookupError`. (done)

```python
popup = page.fields["category"].add_related()
popup.populate(name="Toys")

result = popup.save()
assert result.success                                     # done
assert result.page is page                                # done
assert page.fields["category"].value.label == "Toys"      # done

popup = page.fields["category"].change_related()
popup.fields["name"].fill("Games")
assert popup.save().success                               # done
assert page.fields["category"].value.label == "Games"     # done
```

A field without the icon asked for raises `LookupError`, such as when the user may not add or
change the related objects, or when the field has several objects, which the admin draws no pencil
for. So does `change_related()` while the field has nothing chosen. A page the admin refuses to
open in the popup comes back as a page opened directly does, to say how it was refused. (done)

The magnifying glass the admin draws next to a raw-ID input opens the related model's changelist in
a popup. `field.choose_related()` clicks it and returns that changelist, which is read, searched,
filtered and sorted like any other. `choose()` on one of its rows clicks the row's link. The admin
then closes the popup and puts the object's id in the input: in place of the one a foreign key
holds, and after those a many-to-many field holds. (done)

```python
popup = page.fields["replacement"].choose_related()
popup.search("bolt")
popup.rows[0].choose()
assert page.fields["replacement"].value == str(bolt.pk)   # done
```

A field without a magnifying glass raises `LookupError`. So does `choose()` on a row without a link,
and on a row of a changelist that wasn't opened from a field. (done)

---

# 14. Form Population (done)

The package must support automatic form population.

The caller may provide values from either:

1. a dictionary; (done)
2. an object. (done)

A single field is filled on its own, in the terms it is read back in: a checkbox by the
truth of what it is given, a select by the option standing for it, anything else by the
text of the value:

```python
page.fields["name"].fill("Widget")                          # done
page.fields["price"].fill(Decimal("19.99"))                 # done
page.fields["released_on"].fill(date(2026, 1, 15))          # done
page.fields["is_active"].fill(False)                        # done
page.fields["category"].fill(str(tools.pk))                 # done
page.fields["featured"].fill(None)                          # done
```

Giving a select a value none of its options has fails at once, naming the field and listing
the options it offers. (done)

---

## 14.1 Dictionary source (done)

Example:

```python
data = {
    "name": "Widget",
    "price": "19.99",
    "description": "Example",
}

page.populate(data)
```

Only fields represented on the current admin form should be considered. A field the source
says nothing about is left as the page rendered it, and one the user may only read is passed
over. (done)

The fields filled are the ones the form shows when population starts. A field a script adds
while the others are being filled, as a project's widget may, is not filled; populating again
fills it. (done)

Unrelated dictionary keys are ignored. A key that names no field of the form populates
nothing, and the test that relied on it fails on what it asserts next. (done)

---

## 14.2 Object source (done)

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
name. An attribute the object does not have leaves that field alone, and a property is read
like any other attribute. (done)

Django model instances should naturally be usable:

```python
page.populate(product)    # done
```

A related object stands for the option the select offers for it, so a foreign key set on the
instance picks that option. (done)

A many-to-many field is filled with the related objects of a saved instance. An unsaved one has
none yet, so the field is left as rendered. (done)

A file field is filled with the file the instance stores, uploaded again, so the new object gets
a copy of it. One that stores none leaves the field empty. (done)

This does not imply that related objects or object graphs must automatically be serialized in
1.0.0.

---

## 14.3 Keyword values (done)

Values may also be given as keyword arguments, on their own or next to a source. A keyword
adds a field the source lacks or overrides the value the source has for it:

```python
page.populate(product, name="Renamed", category=None)    # done

page.populate(name="Widget", price="19.99")              # done
page.populate(data, name="Renamed")                      # done
```

The source and the mode of section 15 are positional, never keywords, so every keyword is a
field's value and a form field named `source` or `mode` is given like any other. (done)

---

# 15. Population Modes (done)

Three population modes are required.

## Required fields only

```python
page.populate(data, "required")
```

Only required fields are populated. The mode says which fields are looked up, so data for
the others may sit in the source unused. (done)

---

## Optional fields only

```python
page.populate(data, "optional")
```

Only non-required fields are populated. A field the user may only read is in no mode. (done)

---

## All fields

```python
page.populate(data, "all")
```

All supported fields for which values are available are populated. This is what populating
without a mode does. (done)

The modes are the members of one enum, `PagePopulationMode`, so neither the package nor a
project spells them out by hand:

```python
from django_admin_kit.pages import PagePopulationMode

page.populate(data, PagePopulationMode.REQUIRED)
```

A plain string is accepted and converted, so `PagePopulationMode.REQUIRED` and `"required"`
are the same call; a string that is no mode fails on the enum's own `ValueError`.

---

# 16. Form Submission (done)

Create and edit pages submit whatever the form holds when the submission is made. Filling the
form (sections 14 and 15) and submitting it are separate steps, so a test fills a form the way
it needs and then submits it:

```python
page = admin_ui.create(Product)

page.populate(data, PagePopulationMode.REQUIRED)

result = page.save()

assert result.success
```

Editing:

```python
page = admin_ui.edit(product)

page.populate(name="New name")

result = page.save()

assert result.success
```

---

## 16.1 Submit actions (done)

A form offers a set of actions, not a single submit.

An action is a button that submits the form, and it is named exactly as the button is: by
the `name` it posts, which is also what the admin's view checks for. Nothing is translated, so
a test uses the name written in the template and in the view, underscore included:

```python
page = admin_ui.edit(product)

assert page.actions == {
    "_save",
    "_continue",
    "_addanother",
}
```

The admin's own actions are also available as constants, so a test need not type their names:

```python
from django_admin_kit.pages import FormAction

assert page.actions == {
    FormAction.SAVE,
    FormAction.SAVE_AND_CONTINUE,
    FormAction.SAVE_AND_ADD_ANOTHER,
}
```

Each constant is the name it stands for, so constants and names mix freely, in a set as
anywhere else.

Presence of any action:

```python
assert page.has_action(FormAction.SAVE_AND_CONTINUE)
assert not page.has_action("_approve")
```

Each standard action has its own check, since these are the ones a test asks about most:

```python
assert page.can_save
assert page.can_save_and_continue
assert page.can_save_and_add_another
assert not page.can_save_as_new
assert not page.can_delete
```

"Save as new" is offered only by an admin that turns on `save_as`, on an edit page, where it
takes the place of "Save and add another":

```python
page = admin_ui.edit(feed)

assert page.actions == {
    FormAction.SAVE,
    FormAction.SAVE_AND_CONTINUE,
    FormAction.SAVE_AS_NEW,
}
```

Each standard action has its own method:

```python
result = page.save()
result = page.save_and_continue()
result = page.save_and_add_another()
result = page.save_as_new()
```

`submit` is the lower-level call these methods are built on. It invokes any action by its name,
so an action the admin defines itself is addressed the same way, and it always takes the
action, with no default:

```python
assert page.has_action("_approve")

result = page.submit("_approve")
```

Invoking an action the page does not offer, through its own method or through `submit`, raises
an error that names the actions the page does offer. Nothing is submitted, so the page stays
as usable as it was.

Deleting is not an action. The admin offers it as a link to the confirmation page of section
23.4, which submits nothing, so it is not in `actions`, as the "Close" link shown to a user who
may not save is not either. It has its own check and its own method, and deletion takes the
admin's two steps: `delete` follows the link to the confirmation page, and `confirm_deleting`
on that page performs the deletion:

```python
assert page.can_delete

confirmation = page.delete()

assert confirmation.can_confirm_deleting

result = confirmation.confirm_deleting()
```

`delete` returns the confirmation page itself, as opening it would, since following a link has
no outcome to report; `confirm_deleting` returns a result like any submission.

`delete` on a page that offers no delete link raises an error, and leaves the page as it was.

---

## 16.2 Post-submission navigation (done)

The result reports where the admin sent the user.

Any destination can be checked directly:

```python
result = page.save()

assert result.success
assert result.redirected_to(admin_ui.url.list(Product))
```

```python
result = page.save_and_continue()

assert result.redirected_to(admin_ui.url.edit(product))
```

`redirected_to` accepts any admin URL of section 6.3 and compares under that section's
normalization, so a test never depends on whether the admin redirected in relative or absolute
form.

Shorthands are provided for the destinations the standard actions lead to, each taking what the
matching URL of section 6.3 takes:

```python
assert result.redirected_to_index()
assert result.redirected_to_list(Product)
assert result.redirected_to_create(Product)
assert result.redirected_to_edit(product)
```

The page the admin sent the user to is the result's page, and anything the shorthands do not
cover is read from it (section 16.4):

```python
assert result.page.destination == admin_ui.url.list(Product)
```

---

## 16.3 Forms with no submit actions (done)

A form on which the admin offers no actions at all is a supported, assertable state:

```python
page = admin_ui.edit(report)

assert page.works
assert page.actions == set()
```

---

## 16.4 The page after a submission (done)

A submission moves the browser on, and every result carries the page the browser shows
afterwards, whatever the admin made of the submission: the page it redirected to, or the same
form rendered again when it rejected it. That page is the only way to it: the result reports on
the submission and never repeats what the page says.

When the browser stays on the page that was submitted, the result's page is that same page
object. That is a form the admin rejected and rendered again, "Save and continue" on an edit
page, and "Save and add another" on a create page. Since every read is live (section 3.9), the
page the test already holds reads the page as it is now:

```python
result = page.save()

assert not result.success
assert result.page is page
assert page.fields["price"].value == "19.99"
```

When the browser moves to another page, the result's page is a new page object of the type
its URL names, and the page that was submitted fails at once when it is read, or anything taken
from it is, saying where the browser is now:

```python
result = page.save()

assert result.success
assert result.page.count == 1

page.fields["name"].value    # raises: the browser has left this page
```

Whether a page object stays usable depends on where the browser is, never on whether the admin
accepted the submission: "Save and continue" succeeds and keeps the page, "Save" succeeds and
leaves it.

An action the page does not offer submits nothing, so it leaves the page as it was.

---

# 17. Create Validation Testing (done)

The package must make it easy to intentionally submit invalid create forms.

Example:

```python
page = admin_ui.create(Product)

page.populate(name="")

result = page.save()

assert not result.success
```

The rejected form, the result's page, must expose its validation errors independently of HTML
markup.

---

# 18. Edit Validation Testing (done)

The same validation interface must apply to edit forms.

Example:

```python
page = admin_ui.edit(product)

page.populate(name="")

result = page.save()

assert not result.success
```

Create and edit validation should use the same public error representation.

---

# 19. Re-render After Invalid Submission (done)

An invalid submission brings the form back carrying what was submitted, on the result's
page: (done)

```python
page = admin_ui.create(Product)

page.populate(name="", price="19.99")

result = page.save()

assert not result.success
assert result.page.fields["price"].value == "19.99"    # done
```

The re-rendered form is the result's page (section 16.4), the same page object that was
submitted, read as it is now (section 3.9). It exposes the full field API of sections 10 to 13,
so requiredness, choices, and rendered-only state remain inspectable after a failed submission.
(done)

A browser never keeps a chosen file, so a file field comes back as the admin renders it: empty
on a create page, and holding the stored file on an edit page from Django 4.2. Earlier versions
put what was posted in the stored file's place, so the field shows none and reads as `None`. A
"Clear" that was checked comes back checked from Django 5.0, so the field still reads as `None`;
Django 4.2 renders it unchecked, so the field reads as the stored file. (done)

```python
page = admin_ui.edit(manual)
page.populate(title="", file="tests/data/b.pdf")

result = page.save()

# Django 4.2 and later
assert result.page.fields["file"].value == ("manuals/a.pdf", "/media/manuals/a.pdf")    # done
```

---

# 20. Validation Error Model (done)

Validation errors are divided into three levels:

* the summary notice the admin displays;
* form-level errors that belong to no single field;
* field-level errors.

They are read from the form that shows them, the result's page after a rejected submission
(section 16.4). A create or edit page that has not been submitted shows none:

```python
assert not page.errors

result = page.save()

assert result.page.errors
```

`page.errors` is true when any of the three levels shows something.

---

## 20.1 Summary notice (done)

The admin displays a notice when a submission fails.

```python
assert result.page.errors.banner
```

Its exact wording varies with the number of errors and between Django versions. A test that
only cares that the submission was rejected should assert truthiness.

Where a test does assert the text, the normalized message is available, and `""` on a
page that shows no notice:

```python
assert result.page.errors.banner == "Please correct the error below."
```

---

## 20.2 Form-level errors (done)

Validation messages that belong to the form rather than to any single field are exposed
separately from the summary notice:

```python
assert result.page.errors.non_field == [
    "At least one plan must be default.",
]
```

The summary notice and form-level errors are distinct concepts and must not be conflated.

---

## 20.3 Field errors (done)

Errors for an individual field are read from the field they belong to, addressed by name as
in section 10:

```python
assert result.page.fields["name"].errors == [
    "This field is required.",
]
```

A field may fail several rules at once, so its errors are a list, in the order the admin shows
them, and `[]` for a field with none:

```python
assert result.page.fields["sku"].errors == [
    'A SKU must start with "SKU-".',
    "A SKU must not contain spaces.",
]
```

---

# 21. Validation Error Matching (done)

Tests should be able to perform both exact and partial validation checks.

Exact:

```python
assert result.page.fields["name"].errors == [
    "This field is required.",
]
```

Contains:

```python
assert "This field is required." in result.page.fields["name"].errors
```

Complete error-set testing:

```python
assert result.page.errors.fields == {
    "name": ["This field is required."],
    "email": ["Enter a valid email address."],
}
```

`errors.fields` holds only the fields that show errors, so a field it leaves out has none.

---

# 22. Operation Messages (done)

The admin reports the outcome of an operation to the user.

The admin shows them on whichever page follows the operation, so they are read from any admin
page, the result's page after a submission (section 16.4). Messages are exposed with their level
and their normalized text, independently of markup:

```python
page = admin_ui.create(Product)

page.populate(data)

result = page.save()

assert result.page.messages == [
    ("success", "The product “Widget” was added successfully."),
]
```

`page.messages` is a sequence of messages in the order the page shows them, so it is
indexed, iterated and compared like a list. Each message is a `Message` with a `level` and a
`text`, and compares equal to a `(level, text)` pair written as a tuple or a list:

```python
message = result.page.messages[0]

assert message.level == "success"
assert message.text == "The product “Widget” was added successfully."
```

A level is the tag the project gives it, not a fixed name. Django's defaults are `debug`,
`info`, `success`, `warning` and `error`, and a project renames them or adds levels of its own
through `MESSAGE_TAGS`; the page shows only the tag, so a project that tags errors `danger`
reads them as `danger`. The levels a page knows are Django's defaults merged with the
project's `MESSAGE_TAGS`.

The messages of one level are read by its name, as their texts in order, and `[]` when the
page shows none of that level:

```python
assert result.page.messages.of_level("success") == [
    "The product “Widget” was added successfully.",
]
assert not result.page.messages.of_level("error")
```

A level the project does not have raises `KeyError` that lists the levels it does have,
rather than reading as no messages. Otherwise a test asking for `error` in a project that
renamed it would find none and pass whatever the page showed:

```text
KeyError: "The project has no message level 'error'. Levels: 'debug', 'info', 'success', 'warning', 'danger'."
```

A message's level is the one known level tag among the classes the admin draws for it. Any
extra tags the project added are not part of it, and a message whose level has no tag reads
with the level `""`, which `of_level("")` reads too.

Messages are read even from a page that did not open where it was asked, because the page
the admin sent the user to is where it reports why. A user who asks for an object that does
not exist is sent to the index with a warning (section 6.1), and the page that reports
`missing` reads it:

```python
page = admin_ui.edit(product)    # deleted meanwhile

assert page.missing
assert page.messages.of_level("warning") == [
    "Product with ID “1” doesn’t exist. Perhaps it was deleted?",
]
```

Django shows a message once, so opening the index again would not show it. Every other reader
still refuses a page that did not open.

Messages are distinct from validation errors. A successful operation leads to a page with
messages and no errors; a rejected one to a form with errors and possibly no messages at all.

---

# 23. CRUD Success Checks (done)

The package must support basic create, edit, and delete workflows.

The result of an operation says whether the admin accepted it (section 16.2). What was stored
is the test's to check, through the ORM it already uses: the test knows the object it edited
and what it filled in for a new one. The package does not look stored objects up for it, since
a plain "Save" redirects to the changelist and names no new object.

## 23.1 Create (done)

```python
page = admin_ui.create(Product)

page.populate(name="Widget", sku="SKU-1", price="10.00")

result = page.save()

assert result.success    # done

product = Product.objects.get(sku="SKU-1")
assert product.name == "Widget"
```

---

## 23.2 Edit (done)

```python
page = admin_ui.edit(product)

page.populate(name="Updated widget")

result = page.save()

assert result.success    # done

product.refresh_from_db()
assert product.name == "Updated widget"
```

---

## 23.3 Delete (done)

```python
result = admin_ui.delete(product).confirm_deleting()

assert result.success
```

The same deletion can start from the edit page, as in section 16.1:

```python
result = admin_ui.edit(product).delete().confirm_deleting()

assert result.success
```

---

## 23.4 Delete confirmation contents (done)

The confirmation page lists what the deletion will remove: the object itself, then every
related object it takes with it, in the order the page shows them. Each one reads as the page
writes it, the model's name and the object's text:

```python
page = admin_ui.delete(product)

assert page.works

assert page.deletions == [    # done
    "Product: Widget",
    "Review: Great",
    "Review: Fine",
]
assert "Review: Great" in page.deletions    # done
```

The entries are texts, not model instances. The admin links an entry to its object only when
the site registers the object's model, and related objects of unregistered models are common,
such as a many-to-many's through rows or models edited only inline, so a list of instances would
leave them out. The page draws the list nested, each object over the related objects it takes
with it; `deletions` reads it top to bottom and drops only the indentation.

The page also counts what the deletion will remove, per model, as its "Summary" shows it:

```python
assert page.deletion_counts == {"Products": 1, "Reviews": 2}    # done
assert "Categories" not in page.deletion_counts             # done
```

The keys are the labels the page shows, since the page names each model by nothing else. A
model the deletion removes none of is not counted, and reading it raises `KeyError` listing the
models the page does count, so a misspelt label fails rather than reading as none:

```text
KeyError: "The page counts no model 'Categories'. Models: 'Products', 'Reviews'."
```

The sentence the page starts with is read as shown:

```python
assert page.intro == (    # done
    "Are you sure you want to delete the product “Widget”? "
    "All of the following related items will be deleted:"
)
```

Its wording depends on whether the deletion can be confirmed, on the Django version, which
changed its quote marks in 6.0, and on the language, so a project decides how far to rely on it.

A page that cannot be confirmed (section 23.5) removes nothing: `deletions` is `[]` and
`deletion_counts` is `{}`.

The confirmation "Delete selected" leads to on a changelist reads the same way (section 8.7).
Its `deletions` list each selected object, followed by what it takes with it, one after the
other.

---

## 23.5 Deletion refused (done)

An admin may decline to offer or to perform a deletion.

The absence of the action is assertable: (done)

```python
page = admin_ui.edit(product)

assert not page.can_delete    # done
```

So is a confirmation page that offers no way to confirm, as when related objects protect the
one being deleted: (done)

```python
page = admin_ui.delete(category)

assert not page.can_confirm_deleting    # done
assert page.blockers == ["Product: Widget"]    # done
```

`blockers` is what the page lists in place of the deletions: the objects that protect the one
being deleted, as above, or the kinds of object the deletion would take with it that the user
may not delete, such as `["product"]`. The admin draws both lists alike and tells them apart
only in its translated sentence, so `blockers` is one list and `intro` says which case it is:

```python
assert page.intro == (    # done
    "Deleting the category “Tools” would require deleting the following protected "
    "related objects:"
)
```

The page shows either what the deletion removes or what blocks it, never both: `blockers` is
`[]` on a page that can be confirmed, and `deletions` is `[]` on one that cannot. When a deletion
is blocked both ways, the admin lists only the kinds the user may not delete, so `blockers` reads
those and the protected objects are not on the page. Django collects both lists into sets, so the
order of several entries is not fixed.

So is a refused operation: (done)

```python
result = admin_ui.delete(product).confirm_deleting()

assert not result.success    # done
```

The admin refuses a confirmation it offered when things changed after the page opened: the
object became protected, and the admin shows the confirmation again with its blockers, or the
admin no longer lets the user delete it, and answers that the user is denied.

A confirmation for an object someone else deleted after the page opened is not refused: the
admin sends the user to the index with a warning, as for any missing object (section 6.1), so
`result.success` is true and the result's page says what happened:

```python
assert result.page.messages.of_level("warning") == [    # done
    "Product with ID “1” doesn’t exist. Perhaps it was deleted?",
]
```

---

# 24. Admin Index and Model Exposure (done)

The package must expose what the admin presents to the current user.

```python
page = admin_ui.index()    # done

assert page.works          # done
```

Which models are exposed:

```python
assert Product in page.models     # done
assert Category in page.models    # done
```

How they are grouped, in the order presented:

```python
assert page.apps == [                     # done
    "Shop",
    "Authentication and Authorization",
]

assert page.models_for("Shop") == [
    Product,
    Category,
]
```

Model exposure reflects the current user. A model the user may not see is not listed, and
an app none of whose models the user may see is not listed either. (done)

---

# 25. Page Object Model (done)

The public API should conceptually expose these page/result types.

```text
AdminSession
│
├── AdminUrls
│
├── AdminPage            (any admin URL — section 6.5)
├── IndexPage
├── ChangelistPage
├── CreatePage
├── EditPage
├── DeletePage           (the confirmation the admin asks for before deleting)
│
├── ChangelistColumn     (one changelist column, section 7.3)
│
├── ChangelistFilters    (a changelist's filters by field, section 8.4)
│   └── FieldFilters     (the filters on one field)
│       └── FieldFilter
│
├── Fieldset
├── FormField
│   ├── FieldChoice
│   └── FormFile
├── actions              (a set of action names, section 16.1)
├── Row
├── Cell
│
├── ValidationErrors     (on a create or edit page)
├── Messages             (on any page)
│   └── Message
│
└── SubmissionResult
    └── page             (the page the submission led to, one of the above)
```

The exact Python class names are implementation details, but the public concepts should remain
recognizable and stable.

Every type above that stands for something on the page exposes a native handle, as described
in section 3.6. `AdminUrls`, `FieldChoice`, `FormFile` and `actions` are values with no
element behind them, so they have none. (done)

A `SubmissionResult` reports on a submission rather than standing for anything on the page, so
it has none either; the page it carries has one. (done)

A `ChangelistColumn`'s handle is its header cell. (done)

`ChangelistFilters` is a mapping of groups rather than an element, so it has none. A
`FieldFilter`'s handle is its list of links, and a `FieldFilters` handle is that list, or a list
of them for a field with several filters. (done)

---

# 26. Example 1.0.0 Tests

## Authentication and permissions

```python
def test_staff_access(admin_ui, staff_user, product):
    admin_ui.login(staff_user)

    assert admin_ui.list(Product).works      # done
    assert admin_ui.edit(product).works      # done
    assert admin_ui.delete(product).denied   # done
```

---

## Basic page health

```python
def test_product_admin_pages(admin_ui, admin_user, product):
    admin_ui.login(admin_user)

    assert admin_ui.list(Product).works      # done
    assert admin_ui.create(Product).works    # done
    assert admin_ui.edit(product).works      # done
    assert admin_ui.delete(product).works    # done
```

---

## Model exposure

```python
def test_shop_models_are_exposed(admin_ui, admin_user):
    admin_ui.login(admin_user)

    page = admin_ui.index()

    assert page.models_for("Shop") == [    # done
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

    assert page.count == 3    # done

    assert page.headers == [    # done
        "ID",
        "First name",
        "Last name",
        "Email",
        "Status",
    ]

    assert page.match([    # done
        (1, "Jane", "Doe", "", ANY),
        (2, "John", "Doe", lambda row, cell: "@" in cell.value, ANY),
        ANY_ROW,
    ])
```

---

## Changelist by column

```python
def test_customer_status(admin_ui, admin_user):
    admin_ui.login(admin_user)

    page = admin_ui.list(Customer)

    assert page.contains({    # done
        "first_name": "Jane",
        "is_active": True,
    })
```

---

## Empty changelist

```python
def test_empty_customer_list(admin_ui, admin_user):
    admin_ui.login(admin_user)

    page = admin_ui.list(Customer)

    assert page.works         # done
    assert page.empty         # done
    assert page.count == 0    # done
```

---

## Form structure

```python
def test_product_create_fields(admin_ui, admin_user):
    admin_ui.login(admin_user)

    page = admin_ui.create(Product)

    assert set(page.fields) == {    # done
        "name",
        "price",
        "description",
        "enabled",
    }

    assert page.fields["name"].required                 # done
    assert page.fields["price"].required                # done
    assert not page.fields["description"].required      # done

    assert page.fields["name"].label == "Name"          # done
    assert page.fields["enabled"].value is True         # done

    assert page.fields["category"].choices == [    # done
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

    assert not page.fields["created_at"].editable    # done
    assert page.actions == set()    # done
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
    }, PagePopulationMode.REQUIRED)    # done

    result = page.save()

    assert result.success    # done
    assert result.redirected_to_list(Product)    # done
    assert result.page.messages.of_level("success")    # done
```

---

## Validation

```python
def test_product_validation(admin_ui, admin_user):
    admin_ui.login(admin_user)

    page = admin_ui.create(Product)

    page.populate(name="", price="")

    result = page.save()

    assert not result.success    # done

    assert result.page.errors.banner    # done

    assert result.page.fields["name"].errors == [    # done
        "This field is required.",
    ]

    assert result.page.fields["price"].errors == [    # done
        "This field is required.",
    ]
```

---

## Re-render after an invalid submission

```python
def test_product_form_is_rendered_back(admin_ui, admin_user):
    admin_ui.login(admin_user)

    page = admin_ui.create(Product)

    page.populate(name="", price="12.00")

    result = page.save()

    assert not result.success    # done

    assert result.page.fields["price"].value == "12.00"    # done
```

---

# 27. Public Fixtures (done)

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

`admin_ui` is assembled from five session-scoped fixtures, and a project adjusts it by
overriding one of them at whatever scope pytest allows, keeping the rest:

```python
admin_ui_config         # the settings of section 28, resolved and validated once
admin_ui_urls           # the URLs of section 6.3 for the site under test; see section 29
admin_ui_normalizers    # the rules of section 28.3 that read rendered values
admin_ui_widgets        # the widget classes of section 28.5 that read and fill controls
admin_ui_driving        # keeps Django's ORM usable while a browser is running
```

The first four are the intended extension points. Overriding `admin_ui_normalizers` or
`admin_ui_widgets` in a `conftest.py` or a test module replaces the rules or the widget classes
for those tests without restating the rest of the settings. A single test replaces either by
parametrizing the fixture's name, as pytest allows for any fixture:

```python
@pytest.mark.parametrize("admin_ui_normalizers", [Normalizers({"date": as_date})])
def test_release_dates(admin_ui, admin_user):
    ...
```

The fifth exists so that it is set up before the test database and torn down after it, and a
project has no reason to replace it. (done)

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

# 28. Configuration and Extensibility (done)

The package must be generic and adjustable to every project's needs.

Nothing project-specific ships in the package. Every project-specific behavior enters through a
documented extension point.

## 28.1 Configuration surface (done)

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
* value normalization (done);
* field handling, by widget class (section 28.5) (done).

How the browser itself is chosen and shown is **not** configured here. See section 28.4. (done)

---

## 28.2 Admin location (done)

The admin URL prefix is **not** assumed to be `/admin/`. URLs are resolved from the admin site
under test.

---

## 28.3 Normalization rules (done)

All normalization described in section 3.4 is defined by settings, not by package internals.

The package ships a complete default rule set, one rule per kind of value the admin renders.
The package decides which rule reads a value, so a rule handles one kind and never has to tell
the kinds apart:

* `boolean`: booleans drawn as icons, read as `True`, `False` or `None`;
* `empty`: values the admin has none of, shown as the text it renders for them;
* `link`: links, read as their text, with their targets in `links`;
* `date`, `datetime` and `time`: dates, date-times and times, each shown as the text the
  project's formats render;
* `number`: numbers, shown as the text the project's formats render;
* `choice`: the display value of a choice, shown as its label;
* `text`: everything else, as its text with surrounding whitespace collapsed.

Every default but `boolean` returns the text, so a value reads as the user reads it until the
project replaces the rule for its kind. Dates, date-times and times are three rules, because a
project that types them wants a `date`, a `datetime` or a `time` back and parses each
differently.

A rule is a callable that takes the rendered value, the same object a changelist cell or a
rendered-only field reads from (its `text`, `links` and `native`), and returns the value a test
reads. It also gets `field`, the model field behind the value, or `None` for a value that has
none, such as a method column, and `empty_display`, the text the admin shows there for a value
it has none of.

The rule for a value is picked by what stands behind it, first by the model field of its
changelist column or of its rendered-only form field, then by what the admin drew. The first of
these that applies wins:

1. `empty`, when the text is what the admin shows for a value it has none of there: on a
   changelist, the display function's own `empty_value` for a method or a callable that sets
   one, else the model admin's empty value display, else the site's; on a form, the model
   admin's, else the site's, as the admin itself resolves it;
2. `choice`, when the field has choices, which the admin renders as their labels whatever the
   field's class;
3. the kind for the field's class, the most specific first: `boolean` for a boolean field, `date`
   for a date field, `datetime` for a date-time field, which Django makes a kind of date field,
   `time` for a time field, and `number` for an integer, decimal or float field;
4. for a value no field gives a kind to: `boolean` when the admin drew a lone boolean icon, as
   for a method with `boolean=True`, else `link` when the value renders links;
5. `text`.

A linked date column is therefore read by `date`, its links still in `links`. A value with no
field behind it, such as a method's result, is never read by a field's kind: the admin renders
it as text and says nothing of its type. An empty string is drawn as nothing, so it reads as
`text`; and since the admin marks an empty value in no other way, a value whose text is the
empty display itself reads as `empty`.

A project replaces a rule in its settings, naming it by its dotted path, as it names the admin
site: importing it in the settings module would import project code before Django's app
registry is ready. A project that wants a date column read as a date replaces that one rule,
and it receives only the values of date fields:

```python
DJANGO_ADMIN_KIT = {
    "normalizers": {
        "date": "shop.rules.as_date",
    },
}
```

The names are `boolean`, `empty`, `link`, `date`, `datetime`, `time`, `number`, `choice` and
`text`. The rules are imported and checked once, with the rest of the settings (section 28.4):
a name that is none of these, a value that is not a string, a path that does not import and
one that names no callable are each rejected, naming the rule and, for a name, listing the
names there are.

Two things must hold:

* **Any rule can be overridden.** A project replaces a single rule without restating the rest.
  The defaults it does not mention stay in force.
* **No rule is privileged.** Nothing is hardcoded, and no override requires modifying or
  subclassing package internals.

Rules apply to what the admin renders for the user to read: changelist cells and rendered-only
form fields. An editable field's value is what its control holds (section 13), and goes through
no rule.

Overrides apply project-wide. The rules are built once per session into the
`admin_ui_normalizers` fixture (section 27), which a project may override for a directory or a
module of tests, or parametrize for a single test. Adding a rule for a representation the
package does not know is left for later (section 33).

---

## 28.4 Browser settings (done)

The package does not own the browser. It takes one from the established pytest plugin for
browser testing, and that plugin's own options decide which browser runs, whether it is visible,
how far it is slowed down, and what is recorded while it runs.

This is deliberate. A project that already tests through a browser has those options set and its
authors know them; a second vocabulary meaning the same thing would give every such project two
places to say one thing, and a test suite converted to this package would have to be reconfigured
to get behavior it already had.

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
does to a test session, including behavior a project did not ask for, and adopting the package
means adopting it. And a test's identity carries the browser it ran on, per section 27.

Configuration errors must be loud. An unrecognized setting is rejected, naming the key and
listing the valid ones, because a silently accepted typo disables a setting invisibly. A setting
that used to be part of this package and has since moved is therefore reported as unknown rather
than ignored. Settings are validated once, before the first page is opened, not at the moment
each is first read.

---

## 28.5 Field handling hooks (done)

A project must be able to teach the package how to read and how to fill a field representation
the package does not know.

Once registered, such a field participates in field inspection, population, and submission like
any other.

Most of what a field tells a test comes from the box the admin draws around it and holds for any
widget: its name, label, requiredness, whether it is editable, and its errors. Only three things
depend on the control inside: `value`, `fill` and `choices`. `populate` (section 14) fills
through `fill`, and the check that a form rendered back what was submitted (section 26) reads
through `value`, so a field whose control the package can read and fill takes part in all of
them.

The package reads and fills controls through *widget classes*. A widget class recognizes its
control and says how to read it, fill it and, where it has a fixed set, list its options. Every
method takes the field, whose `native` is its box and `name` its name:

```python
class SwatchPickerWidget:
    def marker(self, field):        # what marks the widget inside the field's box
        return ".swatch-picker"

    def read(self, field):            # what `field.value` returns
        return field.native.locator("input[type=hidden]").input_value()

    def fill(self, field, value):     # what `field.fill(value)` and `populate` do
        field.native.locator(f'button[data-value="{value}"]').click()

    def choices(self, field):         # optional; `field.choices` is [] without it
        return [
            FieldChoice(button.get_attribute("data-value"), button.inner_text())
            for button in field.native.locator("button").all()
        ]
```

`marker`, `read` and `fill` are required and `choices` is optional. A widget class returns
whatever value suits it, and the package passes it on untouched. It never uses `value`, `fill` or
`choices` of the field it is given, which would ask the widget classes again; and `marker`,
which runs for every field the package reads or fills, does not read the page.

The package's own controls are widget classes of the same kind, public so that a project may build
on one: `CheckboxWidget`, `RadioWidget`, `FilteredSelectMultipleWidget`, `AutocompleteWidget`,
`SelectMultipleWidget`, `SelectWidget`, `SplitDateTimeWidget`, `FileWidget`, `RawIdWidget` and
`TextWidget`, tried in that order, the last reading and filling any single control that carries the
field's name as text. They are importable from `django_admin_kit.widgets`.

A widget of several components is one field and one widget class. The admin renders a whole
widget inside its field's box, and fields are found by their box, never by their inputs, so a
split date-time is one field however many inputs it has. Its widget class reaches each part
through the box, a part the widget draws elsewhere on the page through `field.native.page`, and
one inside a frame through `field.native.frame_locator`.

The widget class for a field is the first, in order, whose marker matches something inside the
field's box. Recognizing and acting are two steps. First the package tries the markers of all
widget classes in one browser call, and the first that matches picks the class; what it matched
is not kept. Then it calls `read` or `fill` on that class with the field, whose `native` is the
whole box, and each method finds there the parts it needs. So the marker may be a wrapper around
the controls, or a part that only some renderings of the widget have, and need not be what
`read` and `fill` act on. Since the markers go to the browser together, a marker is a plain CSS
selector as the browser reads it, and the browser layer's own selector syntax is for `read` and
`fill`. A marker combines conditions with `:has()`:

```python
# a file input, only in a box that also holds the upload's cache key
f':scope:has(input[name="{field.name}_cache_key"]) input[type="file"]'
```

A project's widget classes come first, in the order it lists them, and the package's own after
them, in the order checkbox, select, text. So a project replaces one of the package's own by
listing a widget class that matches the same controls, and keeps the rest; one that matches only
some of them, such as the selects a script enhances, takes those and leaves the others to the
package. Hence a marker matches what is particular to its widget rather than the kind of control
it shares with others, which would take every field with that control, and a project lists its
narrower classes before its broader ones. A field no widget class recognizes is reported at
once, naming the field and this setting, rather than after the timeout.

A project lists its widget classes in its settings, by dotted path, as it names the admin site
and its rules. The package makes one instance of each, with no arguments:

```python
DJANGO_ADMIN_KIT = {
    "widgets": [
        "tests.kit_widgets.SwatchPickerWidget",
    ],
}
```

The list is checked once, with the rest of the settings (section 28.4): a value that is not a
list or a tuple of strings, a path that does not import, one that names no class, and a class
without a callable `marker`, `read` or `fill`, or with a `choices` that is not callable, are
each rejected, naming the position in the list. What `marker` returns is checked when it
runs: anything but a non-empty string is reported, naming the widget class.

Widget classes apply to controls, the fields a user may fill. A field the user may only read has
no control, and its value goes through the rules of section 28.3.

The widget classes are built once per session into the `admin_ui_widgets` fixture (section 27),
which a project may override for a directory or a module of tests with its own classes, or
parametrize for a single test; the package's own are added behind them.

---

## 28.6 Project-defined helpers (done)

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

## 28.7 No required base class (done)

No assertion, matcher, or page object may require a project to subclass a package-provided test
case in order to be used.

This preserves the reuse principle of section 3.7: a project composes its own reusable
expectations however it prefers.

---

# 29. Custom Django Admin Sites (done)

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

# 30. Error Reporting (done)

Failure output is an important part of the library.

For example, instead of a generic:

```text
AssertionError
```

a changelist mismatch should expose information such as:

```text
Expected row:
    (1, "Jane", "Doe", ANY)

No matching row found.

Actual rows:
    (1, "Janet", "Doe", "Active")
    (2, "John", "Doe", "Inactive")
```

A form-field failure names the field and the property it was asked about, through pytest's
own rewriting of the assertion: (done)

```text
assert page.fields["email"].required
assert False
 +  where False = FormField('email').required
```

A row match raises `AssertionError` carrying exactly that text, which pytest prints line by
line under the failing statement, as it does for any assertion helper. Everything else is a
plain value, so pytest's own assertion rewriting shows what was compared. (done)

---

# 31. Compatibility Requirement (done)

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
assert page.contains((...))
```

should remain unchanged across supported Django versions. (done)

Version-specific normalization belongs inside the package. This includes differences in how
values are rendered. The admin's own built-in messages are read as the admin words them in the
version under test, and a test that must not depend on that wording asserts what stays the
same: `page.count` rather than `page.summary` (section 8.1), the truthiness of `errors.banner`
(section 20.1), or the parts of `intro` it relies on (section 23.4). (done)

Values render through the formats, time zone and locale the project has configured, and a test
asserts that rendering as the user reads it. A test that covers several locales says which
locale each expected rendering belongs to. (done)

Results must not depend on the machine a test runs on. The browser carries its own notion of
locale and time zone, and the package pins both to what the project has configured, so the same
test yields the same values everywhere. (done)

Where a project has already pinned one of them for its own browser tests, that setting stands.
The package fills in what is unset rather than overriding a deliberate choice, so a project
cannot end up with admin tests running in a different zone from the rest of its suite. (done)

---

# 32. 1.0.0 Acceptance Criteria (done)

1.0.0 is considered complete when a test project can demonstrate all of the following against
supported Django versions:

1. Log in with a superuser. (done)
2. Log in with a staff user. (done)
3. Log in with an arbitrary user object, including one that has no usable password. (done)
4. Verify that a page the user may not open is reported as refused. (done)
5. Verify that model changelist, create, edit, and delete pages work. (done)
6. Read a page's title and subtitle. (done)
7. Read changelist headers, by label and by configured column name. (done)
8. Read the changelist record count and assert an empty changelist. (done)
9. Verify changelist rows, one at a time and as a complete ordered set, using: (done)

    * exact values;
    * `ANY`;
    * callable cell matchers;
    * `ANY_ROW`;
    * column-addressed expected rows.
10. Read normalized boolean cells and link cells including their targets. (done)
11. Inspect fields on create and edit pages. (done)
12. Determine required and optional fields. (done)
13. Read field labels, initial values, choices, and presentation order. (done)
14. Distinguish editable from rendered-only fields and read a rendered-only value. (done)
15. Populate required fields only. (done)
16. Populate optional fields only. (done)
17. Populate all supported fields. (done)
18. Populate from a dictionary. (done)
19. Populate from an object. (done)
20. Submit valid create forms. (done)
21. Submit valid edit forms. (done)
22. Invoke a submit action other than the ordinary save, including one the admin defines. (done)
23. Determine where the admin navigated after a successful operation. (done)
24. Submit invalid create forms. (done)
25. Submit invalid edit forms. (done)
26. Verify that the form rendered the submitted values back after an invalid submission.
    (done)
27. Inspect the admin's summary notice, form-level errors, and field-level errors as three
    distinct levels. (done)
28. Read the messages displayed after an operation. (done)
29. Perform and verify a basic delete operation. (done)
30. Read the contents of a deletion confirmation. (done)
31. Verify that a refused deletion is not offered or not performed. (done)
32. Read the models the admin exposes to the current user, their grouping, and their order.
    (done)
33. Run against a non-default admin site mounted under a non-default URL prefix. (done)
34. Override a default normalization rule and extend field handling from a project, without
    subclassing package internals. (done)
35. Reach a native handle from a page and from a field, and drive a project-specific widget
    with it. (done)
36. Open an arbitrary admin URL and read its access outcome and identity. (done)
37. Run the test suite in parallel. (done)
38. Run the same public test syntax starting with Django 3.2. (done)

---

# 33. Roadmap Beyond 1.0.0

Releases after 1.0.0 are smaller: each brings a few features that belong together, sized by the
work they take rather than by a fixed count, so a project gets each one as soon as it is ready.
The order of the later releases may change as projects adopt the package.

The roadmap covers what Django Admin offers out of the box. What a third-party admin
application or a project's own scripts and templates add is reached through native handles
(section 3.6) and widget classes (section 28.5), so it is not planned here. That includes
nested inlines, which Django does not provide, and previews or other markup a project renders
in a value.

The controls among these arrive as more of the package's own widget classes (section 28.5).
Until then a project reads and fills any of them through a widget class of its own.

---

## 1.1.0: Field details, compound controls and the login page

Field details:

* a field's help text, as the admin shows it with the control: `field.help_text`, `""` for a
  field without one (done);
* named field groups: the fieldsets of a form, in order, each with its name, `None` for a
  group without one, its description, and the names of its fields (done);
* collapsed field groups: whether a group is collapsed, and reading and filling its fields
  without opening it first (done);
* read-only and editable fields: `page.readonly_fields`, the names of the fields the user may
  only read, and `page.editable_fields`, the names of the fields with a control to fill, next to
  the collections of section 12. They follow what the admin renders rather than
  `ModelAdmin.readonly_fields`, so a user who may only view gets every field as read-only.
  Every field is in exactly one of them, and the editable fields are the required and the
  optional ones together (done).

Compound controls, form controls that render several inputs under one name, with their value
and choices:

* split date-times, which the admin draws for every editable date-time field (done);
* radio buttons (`radio_fields`) (done);
* multiple selects (done).

Login page:

* a rejected login: when `login(user, password=...)` is refused, such as for a wrong password,
  reading the error the login form shows, so a test of the login page checks the message as well
  as that the session stayed anonymous. (done)

---

## 1.2.0: Changelist interaction

* search: searching a changelist through its search box, which leads to the changelist of the
  results, the search term it shows, and the count and summary of its results; a changelist
  whose admin declares no search fields reports that it offers no search (done);
* filters: the filters a changelist offers, their choices, and applying them (done);
* ordering: the order a changelist shows, sortable columns, and sorting by them (done);
* pagination and page traversal (done);
* actions: the actions a changelist offers, selecting rows, and running an action, including
  the admin's own "delete selected" and its confirmation (done).

---

## 1.3.0: File and image fields, relational controls

File and image fields:

* the package's own widget class for the admin's file inputs, with and without the
  "Currently" and "Clear" parts (done);
* reading a file field as the file it holds now, a link to it, or `None` (done);
* filling a file field from a path, and clearing an optional one with an empty value (done);
* populating a file field from a model instance, whose stored file is uploaded again (done);
* what a rejected form renders back: a browser never keeps a chosen file, so the field reads as
  it did before the submission (done).

Relational controls:

* many-to-many fields as horizontal and vertical selectors (`filter_horizontal` and
  `filter_vertical`);
* autocomplete fields;
* raw-ID fields;
* related-object popups: adding, changing and choosing a related object from the form;
* related-object automatic population, building related objects from a source.

---

## 1.4.0: Inlines

Reading:

* the inlines of a create or edit page, tabular and stacked, addressed by the prefix their
  formset posts, the way fields are addressed by name, in the order the admin shows them;
* an inline's forms by position, without the hidden template the admin copies new forms from,
  each with the object it stands for and its fields by name, read through the field API of
  sections 10 to 13;
* rendered-only inline fields, read through the rules of section 28.3, links included;
* inline shape: the number of forms, and the initial, minimum and maximum the admin declares;
* what an inline offers: adding another form, and deleting each existing one.

Editing:

* filling and populating an inline form, through the widget classes of section 28.5;
* adding a form through the admin's "Add another" link, up to the maximum the admin declares;
* marking an existing form for deletion;
* inline validation errors at field, form and formset level, the last being errors of the
  whole inline such as a rule across its forms;
* submitting the parent form saves the inlines with it, and a rejected submission renders the
  inline forms back.

One-to-many relationships are edited through inlines, so this release covers them.

---

## 1.5.0: Editable changelists and date hierarchy

* `list_editable`: reading and filling the editable cells of a changelist, and saving them,
  with their validation errors;
* date hierarchy: the levels a changelist offers, and drilling down through them.

---

## Later

* custom admin views and endpoints beyond the standard operations, such as an object's history
  and a user's password change;
* richer row and cell matchers;
* verifying side effects triggered by an admin operation;
* a normalization rule for a value that has no model field behind it, such as a method column,
  chosen by the column rather than by what the admin drew (section 28.3);
* adding a normalization rule for a representation the package does not know, such as a model
  field class of the project's own, which then behaves like any other;
* recognizing a widget by logic of the project's own, where a marker cannot say it, through
  an optional method asked only of the widget classes that define it (section 28.5).
