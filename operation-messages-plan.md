# Operation messages: implementation plan (spec §22)

## Scope

Section 22 of `specification.md`: the messages the admin shows after an operation, read from
any admin page with their level and their text.

What is built:

* `page.messages` on every page (`AdminPage`), a `Messages` sequence of `Message` values in
  the order the page shows them;
* `Message`, with `level` and `text`, comparing equal to a `(level, text)` pair;
* `page.messages.of_level(level)`, the texts of one level, raising `KeyError` that lists the
  project's levels for a level it does not have;
* the level of a message worked out from the classes the admin draws for it, against
  Django's default level tags merged with the project's `MESSAGE_TAGS`, so levels a project
  adds or renames are read by their own tags.

**Out of scope:**

* the links a message renders, such as the object's change link in "The product “Widget”
  was changed successfully.". The text reads the link's text, and `page.native` reaches the
  rest;
* messages a project renders outside the admin's own `ul.messagelist`, such as a template
  that overrides the `messages` block;
* `result.object` and the rest of §23.

## Architecture recap

* `src/django_admin_kit/pages.py`: `AdminPage`, whose readers go through `_shown()`. Every
  page type inherits from it, so a property there reaches the index, changelists, forms,
  delete confirmations and plain pages.
* `src/django_admin_kit/fields.py`: `FieldChoice`, and `src/django_admin_kit/rendered.py`:
  `Link`, the two value classes `Message` follows.
* `src/django_admin_kit/errors.py`: `ValidationErrors`, the model for a live object built
  from a callable that gives an element.
* `src/django_admin_kit/rendered.py`: `text_of`.
* `tests/project/shop/admin.py`: `FeedAdmin`, whose save and "Refresh" button get the
  project's own messages.
* `tests/test_fields.py`: overrides `LANGUAGE_CODE` through pytest-django's `settings`, the
  way the tests here override `MESSAGE_TAGS`.
* `tests/test_submit.py`: `PAGE_READERS`; `tests/test_confirm_delete.py`: `confirming`.

How the admin renders messages, the same on every supported version (checked in the
installed `admin/base.html` of 3.2, 4.2, 5.2 and 6.1):

```html
<ul class="messagelist">
  <li class="{{ message.tags }}">{{ message|capfirst }}</li>
</ul>
```

`message.tags` is the extra tags the code gave the message, then its level tag, separated by
a space; either may be missing. The level tag comes from Django's defaults merged with
`MESSAGE_TAGS`.

## Decisions

1. **`Message` is a value class like `FieldChoice` and `Link`.** It has read-only `level`
   and `text`, compares equal to another `Message` and to a `(level, text)` pair written as
   a tuple or a list, and to nothing else, is hashable, and reads as
   `Message('success', '...')`. It is no tuple, so it is neither indexed nor unpacked, as
   neither of the other two is.
2. **`Messages` is a live sequence.** It is a `collections.abc.Sequence` holding a callable
   that gives the `ul.messagelist > li` items, and reads them each time (§3.9), like
   `ValidationErrors`. Indexing by position and slices, iteration, `len` and `in` come from
   the sequence; it adds truthiness, `==` against a list or tuple of messages or pairs, and
   a `repr` that is the list it reads, so a failing comparison shows what the page said. It
   is not a `list` subclass, because a list would keep what it read.
3. **One level is read through a method, `of_level(level)`, never by `messages["..."]`.**
   `page.messages` indexes by position like any sequence, so a level is not an index too.
4. **The known levels are `django.contrib.messages.utils.get_level_tags()`, read each time.**
   It is Django's own merge of its defaults with `MESSAGE_TAGS`, exactly as §22 defines the
   known levels, so a level the project adds or renames is known by its tag.
5. **A message's level is the last known level tag among its classes, or `""`.** Django
   writes the level tag after the extra tags, so if an extra tag happens to spell a level,
   the level still wins.
6. **`of_level` returns `[]` for a known level the page shows none of, and raises `KeyError`
   for a level the project does not have**, listing the levels it does have in the order
   Django lists them: "The project has no message level 'error'. Levels: 'debug', 'info',
   'success', 'warning', 'danger'." `""` is always accepted, for messages whose level has no
   tag. A renamed level must not read as "none shown" and pass.
7. **`page.messages` is the one reader that also reads a page that did not open.** Every
   other reader refuses such a page, because what it shows is not the page that was asked
   for. Messages are different: they report what happened, and the page the browser landed
   on is where the admin reports it. A user with permission who asks for an object that does
   not exist is sent to the index with "Product with ID “7” doesn’t exist. Perhaps it was
   deleted?" (§6.1), and that page reports `missing` and reads that warning. Django drops a
   message once it is shown, so opening the index again would never show it.
   `messages` therefore runs `_check()` rather than `_shown()`: it still fails at once on a
   page the browser has left, since it would otherwise read another page's messages. The
   exception and its reason are written in a comment next to it.
8. **The test project's own messages come from `FeedAdmin`**, so Django's built-in messages
   stay untouched:
   * `save_model` warns "The source should be a CSV file." with the extra tag `source` when the
     source does not end in `.csv`, and "The source should not contain spaces." with the
     extra tag `info`, which names a level, when it has any. Saving `"new feed.txt"` therefore shows two warnings and Django's success message
     at once:
     several messages of one level, and several levels, on one page. Every feed the suite
     saves today ends in `.csv` and has no spaces;
   * "Refresh" adds "The feed was refreshed." at level 35, which has no tag until a project
     gives it one. It shows on the feed's history page, a plain `AdminPage`.
9. **Both the default and an overridden `MESSAGE_TAGS` are tested in one run.** The test
   project sets no `MESSAGE_TAGS`, so most tests read Django's own tags. A `message_tags`
   fixture in `tests/test_messages.py` overrides the setting for one test through
   pytest-django's `settings`, and also sets `django.contrib.messages.storage.base.LEVEL_TAGS`
   again through `monkeypatch`. Django 4.1 and later do that second step themselves when the
   setting changes; 3.2 and 4.0 compute the value once, at import, so without it the page
   would keep the old tags. With both steps the page renders the override on every version,
   as it would from a `settings.py` that set it, which is how a project sets it. Django's own
   tests do the same. This is in the package's tests only; the package reads the settings.

   The fixture carries a comment that explains this workaround in plain words, so nobody
   removes the `monkeypatch` step as redundant: `MESSAGE_TAGS` is the project's setting and
   `LEVEL_TAGS` is Django's merged table the page is rendered from; Django 4.1 and later
   rebuild the table when the setting changes, 3.2 and 4.0 build it once at import; so the
   fixture rebuilds it too, and pytest puts both back after the test. The comment also says
   it is needed only because a test changes the setting mid-run, and that a project setting
   `MESSAGE_TAGS` in `settings.py` needs nothing.

## New public values

All read-only; nothing here is filled by a user.

| Value | Type | Empty value | Rules |
|---|---|---|---|
| `AdminPage.messages` | `Messages` | falsy, `== []` | any page, including one that did not open; a page the browser left raises `LookupError` |
| `Messages[i]`, iteration | `Message` | none | the order the page shows them |
| `Message.level` | `str` | `""` | the last known level tag among the item's classes |
| `Message.text` | `str` | | whitespace collapsed, link text included |
| `Messages.of_level(level)` | `list[str]` | `[]` | `KeyError` listing the known levels for a level that is neither known nor `""` |

## Commit plan

### M1: Read the admin's own messages with their level

* `src/django_admin_kit/messages.py` (new): `Message` (decision 1) and `Messages(items)`
  (decision 2), the level per decisions 4 and 5.
* `pages.py`:
  * `AdminPage.messages` runs `_check()`, so it fails at once on a page the browser has
    left, and returns `Messages(self._message_items)`;
  * `AdminPage._message_items()` runs `_check()` again and returns
    `self._page.locator("ul.messagelist > li")`. `Messages` calls it each time it reads, so
    a `Messages` held across a navigation fails rather than reading the next page's
    messages. It carries the comment of decision 7.
  * Both use `_check()` and not `_shown()`. `_check()` compares the browser with the page
    the object landed on (`_landed()`), so it passes on a page that did not open, such as
    the index a missing object redirects to; `_shown()` would also refuse that page.
* `tests/test_messages.py` (new):
  * a page opened directly shows no messages: `not page.messages`, `page.messages == []`;
  * an accepted create leads to a changelist showing
    `[("success", "The product “Widget” was added successfully.")]`;
  * "Save and continue" on an edit page shows its message on the same page object (§16.4);
  * a confirmed deletion shows its success message on the changelist;
  * a rejected form shows no messages (§22: errors, not messages);
  * a message has `level` and `text` by name, through `page.messages[0]`, and equals its
    pair as a tuple and as a list but not a bare string;
  * an object that does not exist leads to the index, and the page that reports `missing`
    reads `[("warning", "Product with ID “…” doesn’t exist. Perhaps it was deleted?")]`;
  * a page refused in place (403) reads no messages rather than raising.
* `tests/test_submit.py`: `"messages"` added to `PAGE_READERS`.
* *Consistency:* a new property and a new module; nothing existing reads them.

### M2: The project's own messages, levels and tags

* `tests/project/shop/admin.py`: `FeedAdmin.save_model` with the two warnings, and the
  "Refresh" message (decision 8).
* `tests/test_messages.py`: the `message_tags` fixture (decision 9), with the comment
  that explains the `LEVEL_TAGS` workaround, and:
  * several messages of several levels read in the order shown: saving `"new feed.txt"`
    shows both warnings, then Django's success message. The warnings' extra tags are drawn
    as classes (checked through `native`) and are not part of their level;
  * an extra tag that names a level does not change the level: saving `"new feed.csv"`
    shows only the spaces warning, drawn `info warning`, and it reads `"warning"`;
  * by default, a level without a tag reads `""`, on the history page, a plain `AdminPage`
    (§6.5);
  * a level the project adds reads by its tag: with `{35: "notice"}` the refresh message
    reads `"notice"`;
  * a level the project renames reads by its new tag: with `{30: "caution"}` the warning
    reads `"caution"`.
* *Consistency:* the warnings only show for sources no existing test saves, and the
  refresh message changes nothing the existing "Refresh" tests assert.

### M3: Read the messages of one level

* `messages.py`: `Messages.of_level(level)` per decision 6.
* `tests/test_messages.py`:
  * the success messages of a save, by `"success"`;
  * several messages of one level read together, in order: saving `"new feed.txt"` gives
    both warnings by `"warning"`, and only the success message by `"success"`;
  * a known level with nothing shown reads `[]`;
  * `""` reads the messages without a level tag;
  * a level no project has, such as `"urgent"`, raises `KeyError` listing Django's default
    levels;
  * with `{30: "caution"}`, `of_level("caution")` reads the warning, and `"warning"` raises
    `KeyError` listing the levels with `'caution'` in its place.
* *Consistency:* adds a reader; nothing else changes.

### M4: README and spec

* `README.md`: a "Reading what the admin reported" entry after "Finding out why a form was
  rejected".
* `specification.md`: `(done)` on §1's bullet, §6.5's messages bullet, §22, the §26
  "Required-field population" example and §32 item 28. The §22 wording for `Message`,
  `of_level` and the `KeyError` is already in.
* `operation-messages-plan.md` deleted.

## Verification

`uv run pytest -n auto`, `ruff check`, `ruff format --check`, `mypy src`, then `tox -p 6`
for the eighteen cells, which include Django 3.2 and 4.0, where the `message_tags` fixture
matters.

## Review notes

1. **Where the known levels come from.** Recommended: `get_level_tags()` (decision 4), the
   spec's own definition. Alternative: Django's `storage.base.LEVEL_TAGS`, which is what the
   page was actually rendered with, so it also agrees with the page on Django 3.2 and 4.0
   when a test changes `MESSAGE_TAGS` without the extra step of decision 9. It is a module
   global that Django replaces when the setting changes, so reading it is more tied to
   Django's internals.
