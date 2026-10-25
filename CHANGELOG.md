# Changelog

All notable changes to this project are listed in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Open the login page with `admin_ui.login()`, fill it with `page.fill(username=..., password=...)`
  and submit it with `page.submit()`. A refused form is the same page, so it can be filled
  again. Opening the login page logs nobody out.
- `admin_ui.login(user, password=...)` returns the result of the submission, so
  `result.success` says whether the admin let the user in.
- A submission that ends on the login page has the login page as its `result.page`.
- Read what a login page says with `page.errors`, the notes above the form such as why a login
  was refused, and `page.field_errors`, the errors under each input.
- Read the help the admin shows with a field with `field.help_text`, `""` for a field without
  any. A field the user may only read has it too.
- Get the fields the user may only read and the ones with a control to fill with
  `page.readonly_fields` and `page.editable_fields`. They follow what the page shows, so a user
  who may only view gets every field as read-only.

### Fixed

- `admin_ui.login(user, password="")` no longer waits 30 seconds and fails. The browser does not
  send a form with an empty input, so the result is no success, at once.

## [1.0.0] - 2026-10-13

The first release. Tests open the Django admin in a real browser and check it with plain
`assert` statements.

### Added

- The `admin_ui` fixture. It opens admin pages in a real browser against a live server.
- Log in as any user with `admin_ui.login(user)`. No password is needed, and custom user models
  work.
- Test the login page itself with `admin_ui.login(user, password="...")`.
- Log out with `admin_ui.logout()`.
- Open the index, a changelist, a create page, an edit page or a delete page with
  `admin_ui.index()`, `admin_ui.list(Model)`, `admin_ui.create(Model)`, `admin_ui.edit(obj)` and
  `admin_ui.delete(obj)`.
- Open any other admin page by its path with `admin_ui.open(path)`.
- See if a page opened with `page.works`. See why it did not with `page.denied`, `page.missing`,
  `page.redirected` and `page.status_code`.
- Read the title and subtitle of a page with `page.title` and `page.subtitle`.
- Get admin URLs without writing `/admin/` in tests, with `admin_ui.url.index()`,
  `admin_ui.url.list(Model)`, `admin_ui.url.create(Model)`, `admin_ui.url.edit(obj)`,
  `admin_ui.url.delete(obj)` and `admin_ui.url.login()`.
- Read the models and apps the index shows to the current user with `page.models`,
  `page.apps` and `page.models_for()`.
- Read changelist columns by label with `page.headers` and by name with `page.columns`.
- Read the number of records with `page.count`, and check an empty list with `page.empty`.
- Read rows and cells with `page.rows[0]["email"].value`.
- Read cells as the user sees them: icons become `True`, `False` or `None`, and links become
  their text, with the targets in `cell.links`.
- Check that a changelist has a row with `page.contains(...)`, and check all rows in order with
  `page.match([...])`.
- Use `ANY` for a cell you do not care about, `ANY_ROW` for a row you do not care about, and a
  function for a cell that needs its own check.
- Write an expected row as a tuple of all cells, or as a dictionary of only the columns you care
  about.
- See the expected row and the real rows in the error message when a row does not match.
- Read the fields of a create or edit page by name with `page.fields`, in the order the admin
  shows them.
- Read a field's label, value, choices and errors, and check if it is required or editable.
- Get the required and the optional fields with `page.required_fields` and
  `page.optional_fields`.
- Fill one field with `field.fill(value)`.
- Fill many fields in one call with `page.populate(...)`, from a dictionary, an object, a model
  instance or keyword arguments.
- Fill only the required fields, only the optional fields, or all of them, with
  `PagePopulationMode`.
- See which buttons a form offers with `page.actions`, `page.has_action()` and checks such as
  `page.can_save`.
- Submit a form with `save()`, `save_and_continue()`, `save_and_add_another()`,
  `save_as_new()`, or any button by its name with `submit()`.
- See if the admin accepted a form with `result.success`, and where it went next with
  `result.redirected_to()` and its short forms.
- Read the page the admin showed after a submission with `result.page`.
- Read form errors at three levels: the notice at the top, errors of the whole form, and errors
  of each field.
- Read the messages the admin shows after an action with `page.messages` and
  `page.messages.of_level()`.
- Delete an object in two steps, as the admin does, with `delete()` and `confirm_deleting()`.
- Read what a deletion will remove with `page.deletions` and `page.deletion_counts`, and what
  stops it with `page.blockers`.
- Every value is read from the page at the moment you ask for it, so it is always up to date.
- Reach the Playwright object behind a page, a field, a row or a cell with `.native`.
- Configure the package in one place, the `DJANGO_ADMIN_KIT` setting. Wrong keys and values fail
  at once with a clear message.
- Test another admin site, also one under a different URL prefix, with the `site` setting or the
  `admin_ui_urls` fixture.
- The browser uses the time zone and language of your project, so results are the same on every
  machine.
- Replace any rule that reads values, such as dates or numbers, with the `normalizers` setting.
- Teach the package to read and fill your own widgets with the `widgets` setting.
- Change the rules or the widgets for one folder, one module or one test by overriding the
  `admin_ui_normalizers` or `admin_ui_widgets` fixture.
- Tests can run in parallel, and every test starts logged out.
- Works with Python 3.8 to 3.14 and Django 3.2 to 6.1.

[Unreleased]: https://github.com/JeyKip/pytest-django-admin-kit/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/JeyKip/pytest-django-admin-kit/releases/tag/v1.0.0
