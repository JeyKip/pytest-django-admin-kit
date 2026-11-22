"""The admin's file input: read as the file it holds, stored or chosen, or None, and filled
with the file at a path."""

import pytest
from django.core.files.base import ContentFile

from project.shop.models import Manual

ASSEMBLY = b"Fit the legs, then the top."
WIRING = b"Brown is live, blue is neutral."


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    """Uploads go to the test's own directory. The live server runs in the same process, so
    it stores them there too."""
    settings.MEDIA_ROOT = str(tmp_path / "media")


@pytest.fixture
def manual(db):
    return Manual.objects.create(title="Assembly", file=ContentFile(ASSEMBLY, name="assembly.txt"))


@pytest.fixture
def wiring(tmp_path):
    """A file on disk to choose, outside the media directory, as a path object."""
    path = tmp_path / "wiring.txt"
    path.write_bytes(WIRING)
    return path


def test_an_empty_file_field_reads_as_none(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Manual)

    assert page.fields["file"].value is None


def test_a_stored_file_reads_as_its_name_and_the_link_the_admin_shows(admin_ui, superuser, manual):
    admin_ui.login(superuser)

    page = admin_ui.edit(manual)

    assert page.fields["file"].value == ("manuals/assembly.txt", "/media/manuals/assembly.txt")


def test_a_file_chosen_from_a_path_reads_as_its_name_without_a_link(admin_ui, superuser, wiring):
    admin_ui.login(superuser)
    page = admin_ui.create(Manual)

    page.fields["file"].fill(str(wiring))

    assert page.fields["file"].value == ("wiring.txt", None)


def test_a_file_is_chosen_from_a_path_object(admin_ui, superuser, wiring):
    admin_ui.login(superuser)
    page = admin_ui.create(Manual)

    page.fields["file"].fill(wiring)

    assert page.fields["file"].value == ("wiring.txt", None)


def test_a_chosen_file_is_read_before_the_stored_one(admin_ui, superuser, manual, wiring):
    admin_ui.login(superuser)
    page = admin_ui.edit(manual)

    page.fields["file"].fill(wiring)

    assert page.fields["file"].value == ("wiring.txt", None)


def test_a_file_chosen_on_an_edit_page_replaces_the_stored_one_once_saved(
    admin_ui, superuser, manual, wiring
):
    admin_ui.login(superuser)
    page = admin_ui.edit(manual)

    page.fields["file"].fill(wiring)
    page.save()

    manual.refresh_from_db()
    assert manual.file.name == "manuals/wiring.txt"
    with manual.file.open("rb") as stored:
        assert stored.read() == WIRING


def test_a_path_that_is_no_file_cannot_fill_a_file_field(admin_ui, superuser, tmp_path):
    admin_ui.login(superuser)
    page = admin_ui.create(Manual)
    missing = tmp_path / "missing.txt"

    with pytest.raises(FileNotFoundError) as failure:
        page.fields["file"].fill(missing)

    assert failure.value.args[0] == (
        f"The field 'file' takes the file at a path, and {str(missing)!r} is no file."
    )
    assert page.fields["file"].value is None


def test_a_value_that_is_no_path_cannot_fill_a_file_field(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Manual)

    with pytest.raises(TypeError) as failure:
        page.fields["file"].fill(42)

    assert failure.value.args[0] == "The field 'file' takes a path to a file, not 42."
