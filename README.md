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

Browser binaries aren't needed yet, because no code drives a browser so far. Once that changes:

```bash
uv run playwright install chromium
```

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

## Changing dependencies

Edit `pyproject.toml`, then:

```bash
uv lock                    # update uv.lock
uv sync                    # apply it to .venv
```

Commit `pyproject.toml` and `uv.lock` together.

## The version matrix

This isn't wired up yet. `tox` and `tox-uv` come with the dev group, but there's no `tox.ini`, so
there's nothing to run. It's the next piece of work: 18 cells covering all 9 Django minors, each
on its oldest and newest supported Python.

tox-uv means uv builds those environments, which matters most at the floor: `python3.8 -m venv`
fails with `ensurepip` errors on a lot of systems, and uv sidesteps that by fetching its own 3.8.

Once it exists, spot-check the two extremes locally and leave the full sweep to CI:

```bash
uv run tox -e py310-dj32,py312-dj61
```

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

One thing to leave alone: `pyproject.toml` carries a static `version`, and `__version__` reads it
back from the installed distribution metadata. There's still only one place to change it, and
some IDE integrations reject a dynamic version outright.

## Layout

```
src/django_admin_kit/    the package
tests/                   its own test suite
specification.md         the public API this is built against
```

## License

MIT. See [LICENSE](LICENSE).
