# pytest-django-admin-kit

A pytest toolkit for writing conscious tests against the Django admin.

Tests describe admin pages, their fields, rows, permissions and errors, using ordinary `assert`
statements, and stay unchanged across supported Django versions.

```python
def test_product_admin(admin_ui, admin_user, product):
    admin_ui.login(admin_user)

    assert admin_ui.list(Product).works
    assert admin_ui.edit(product).works
```

Install it as `pytest-django-admin-kit`; import it as `django_admin_kit`.

## Status

Early development. The public API is written up in [specification.md](specification.md) and isn't
implemented yet, so there's nothing here you can point at a real project. What you can do today is
help build it.

## Requirements

Python 3.8 or newer, Django 3.2 or newer.

Development uses [uv](https://docs.astral.sh/uv/) for environments, dependencies and builds. If
you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Setting up

```bash
git clone https://github.com/<your-fork>/pytest-django-admin-kit.git
cd pytest-django-admin-kit

uv sync
uv run pre-commit install
```

`uv sync` creates `.venv`, installs the package in editable mode, and installs the dev tooling
from `uv.lock`. That lock file is committed, so everyone gets the same ruff and mypy and
therefore the same results.

The tests drive real browsers, so you need the binaries too:

```bash
uv run playwright install chromium              # enough for everyday work
uv run playwright install firefox webkit        # the other two the package supports
sudo uv run playwright install-deps webkit      # webkit also needs system libraries
```

Only chromium is required. A test that needs another browser skips itself by name when that
browser isn't downloaded, so a partial install costs you coverage rather than a wall of red. CI
installs all three and fails if anything skips.

## Which Python to develop on

`uv sync` picks an interpreter for you. If you want to choose, use 3.10, and add a 3.12
environment when you need to check Django 6.x:

```bash
uv sync --python 3.10
```

Two reasons this matters more than usual here.

First, don't develop on 3.8. It's been end of life since October 2024, and resolution caps you
there at Django 4.2, playwright 1.48 and pytest 8.3.5. You couldn't run Django 5.x or 6.x locally
at all. CI proves the 3.8 floor for you.

Second, no single interpreter covers every Django version we support. Django 3.2 stops at Python
3.10 and Django 6.1 starts at 3.12, so there's no overlap:

| Python | Django versions it can run |
|---|---|
| 3.8, 3.9 | 3.2 to 4.2 |
| 3.10 | 3.2 to 5.2 |
| 3.11 | 4.1 to 5.2 |
| 3.12 | 4.2 to 6.1 |
| 3.13, 3.14 | 5.1 to 6.1 |

3.10 is the better default because it reaches the Django 3.2 floor, where most version-specific
breakage turns up. You don't need it installed already; uv will fetch it.

## Everyday commands

While you're working, this is the whole loop:

```bash
uv run pytest
```

Before you push:

```bash
uv run ruff check .        # lint
uv run ruff format .       # format in place
uv run mypy                # strict, src/ only
uv run pytest
```

`pre-commit install` already runs ruff and the whitespace checks on every commit, so those first
two mostly buy you faster feedback. To run every hook over the whole tree:

```bash
uv run pre-commit run --all-files
```

## Driving the browser

The browser comes from `pytest-playwright`, so its flags work here and mean what they mean
anywhere else:

```bash
uv run pytest --headed                          # watch it happen
uv run pytest --slowmo 200                      # and slow it down enough to follow
uv run pytest --browser firefox                 # one browser
uv run pytest --browser chromium --browser firefox   # the suite, twice
uv run pytest --video on --tracing on           # artifacts under test-results/
```

Because the browser is theirs, a test's id carries the browser it ran on:
`test_a_superuser_reaches_the_index[chromium]`. Asking for two browsers runs every admin test
twice.

**One thing to know before you install this package anywhere.** `pytest-playwright` registers an
autouse fixture that deletes the `--output` directory, `test-results/` by default, at the start
of **every** pytest session, whether or not the session opens a browser. If your project keeps
JUnit XML or coverage output there, move it or pass `--output` somewhere else. We inherit that
behaviour by depending on the plugin, and there's no way to switch it off.

**Don't pin the live server's port.** `admin_ui` is built on pytest-django's `live_server`, which
binds a free port for each process, so running the suite in parallel with `pytest-xdist` works
out of the box. Setting a fixed address with `--liveserver=localhost:8081` or the
`DJANGO_LIVE_TEST_SERVER_ADDRESS` environment variable makes every worker fight for the same
port. It passes under a single process and fails under `-n`, looking like a flaky port bug
rather than a configuration one.

## The test project

The suite runs against a small Django project in `tests/project/`, wired up by the
`[tool.pytest.ini_options]` table in `pyproject.toml`. You don't have to do anything to use it —
no environment variables, no `manage.py`.

It uses Django's defaults: the admin is at `/admin/` and the user model is `auth.User`. The
things a project can customise are each proved by their own tests, which swap the custom
setup in per test:

- `tests/test_custom_user.py` sets `AUTH_USER_MODEL` to `accounts.User`, a model with no
  `username` field that authenticates by email;
- `tests/test_custom_prefix.py` uses `@pytest.mark.urls("project.urls_backoffice")`, which
  serves the admin at `/backoffice/`;
- `tests/test_custom_site.py` overrides the `admin_ui_urls` fixture to point at `ops_site`, a
  second `AdminSite` mounted at `/ops/` that registers only `Product`.

The swap only works in this direction. `auth.User` is swappable, so a project whose default is
a custom model never creates the `auth_user` table, and no test could swap the default back in.

The database is in-memory SQLite. That is worth knowing when a test feels slow later on: any
test that uses `live_server` is forced onto `transactional_db` by pytest-django, whatever mark
it carries, so the database is rebuilt rather than rolled back. SQLite keeps that cheap.

If you change a model in `tests/project/`, regenerate its migration:

```bash
PYTHONPATH=tests DJANGO_SETTINGS_MODULE=project.settings uv run django-admin makemigrations
```

Those migration files are excluded from ruff so that what's committed stays byte-identical to
what Django generates.

## Changing dependencies

Edit `pyproject.toml`, then:

```bash
uv lock                    # update uv.lock
uv sync                    # apply it to .venv
```

Commit `pyproject.toml` and `uv.lock` together.

## The version matrix

`tox.toml` defines 18 cells: nine Django minors, each on its oldest supported Python at or above
the 3.8 floor and on its newest.

```bash
uv run tox                        # every cell
uv run tox -p 6                   # every cell, six at a time
uv run tox -e 3.8-dj32            # one cell
uv run tox list -d                # what the cells are called
```

Anything after a bare `--` is passed straight through to pytest, so a failing cell can be
picked apart without touching `tox.toml`:

```bash
uv run tox -e 3.10-dj52 -- -x -vv                     # stop at the first failure, verbosely
uv run tox -e 3.10-dj52 -- tests/test_project.py      # just one file
```

The whole sweep takes well under a minute on a warm cache, so there's no reason to leave it to
CI. On a cold one, budget for downloading five interpreters and a copy of Django and playwright
per cell.

tox-uv means uv builds those environments, which matters most at the floor: `python3.8 -m venv`
fails with `ensurepip` errors on a lot of systems, and uv fetches its own 3.8 instead.

Only `pytest-django` is pinned per cell, because no single release spans Django 3.2 to 6.1.
Everything else is left to the resolver, which caps itself per interpreter — 3.8 cells end up on
pytest 8.3.5 and playwright 1.48.0, newer cells on current. That cap is the constraint to design
against: code has to work on playwright 1.48.

There is a second, larger matrix behind the `full` label: the whole cartesian, every Django minor
against every interpreter it supports, 33 cells. It's too slow to sit in front of every pull
request, so it gates releases instead. Run it before tagging one:

```bash
uv run tox -m full -p 8
uv run tox list -m full          # the 33 cell names
```

## CI

Two workflows, both in `.github/workflows/`.

`ci.yml` runs on pull requests and pushes to `main`. It lints, type-checks, runs the 18 cells,
and runs one extra job that exercises firefox and webkit. `release.yml` runs on a `v*` tag: it
runs all 33 cells, then builds, then publishes to PyPI, each job gated on the one before it, so
a matrix failure stops the release rather than merely being recorded next to it.

Browsers are not a Django-compatibility dimension, so they don't multiply the matrix. Each cell
installs chromium — the binary is keyed to that cell's playwright version, which is why tox does
it rather than the workflow — and the separate job covers the other two once.

Neither workflow lists its cells. Both ask tox for them:

```bash
uvx --from 'tox>=4.61' --with tox-uv tox list -d --no-desc -q      # what ci.yml runs
uvx --from 'tox>=4.61' --with tox-uv tox list -m full --no-desc -q # what release.yml runs
```

So editing `tox.toml` changes CI, and the two cannot disagree.

Two things to know before the first release. Publishing uses PyPI's trusted publishing, which
needs the project configured on PyPI to trust this repository and its `pypi` environment — there
is no API token to add. And the build job refuses to run if the tag doesn't match the `version`
in `pyproject.toml`, so bump the version in the same commit you tag.

## Building

```bash
uv build
```

That produces a wheel and an sdist in `dist/`, using the hatchling backend declared in
`pyproject.toml`. uv builds the wheel from the sdist, so a broken sdist fails the build rather
than shipping quietly.

## PyCharm

Recent PyCharm versions support uv directly: point the interpreter at the project and pick uv, or
select the existing `.venv` uv created.

Mark `tests` as a test source root (right-click it, *Mark Directory as* → *Test Sources Root*).
PyCharm doesn't read pytest's `pythonpath` setting, so without this it reports `No module named
project` on the test project's own imports even though everything runs.

One thing to leave alone: `pyproject.toml` carries a static `version`, and `__version__` reads it
back from the installed distribution metadata. There's still only one place to change it, and
some IDE integrations reject a dynamic version outright.

## Layout

```
src/django_admin_kit/    the package
tests/                   its own test suite
tests/project/           the Django project those tests run against
specification.md         the public API this is built against
```

## License

MIT. See [LICENSE](LICENSE).
