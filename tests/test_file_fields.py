"""The admin's file input: read as the file it holds, stored or chosen, or None, filled with
the file at a path or a Django File, and emptied with None or "". An image field has the same
input. A form the admin rejects comes back without the chosen file, as a browser never keeps
one."""

import django
import pytest
from django.core.files.base import ContentFile
from PIL import Image

from project.shop.models import Manual

ASSEMBLY = b"Fit the legs, then the top."
WIRING = b"Brown is live, blue is neutral."
# Django 5.0 renders a rejected form with "Clear" still checked where it was; earlier versions
# render it unchecked.
KEEPS_CLEAR = django.VERSION >= (5, 0)


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


@pytest.fixture
def diagram(tmp_path):
    """An image on disk to choose, outside the media directory."""
    path = tmp_path / "diagram.png"
    Image.new("RGB", (1, 1)).save(path)
    return path


@pytest.fixture
def covered_manual(db, diagram):
    """A manual whose optional cover is stored, so its edit page offers to clear it."""
    return Manual.objects.create(
        title="Assembly",
        file=ContentFile(ASSEMBLY, name="assembly.txt"),
        cover=ContentFile(diagram.read_bytes(), name="front.png"),
    )


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

    assert failure.value.args[0] == (
        "The field 'file' takes a path to a file, a Django File, or None or '' to empty it, not 42."
    )


def test_a_stored_image_reads_as_its_name_and_the_link_the_admin_shows(
    admin_ui, superuser, covered_manual
):
    admin_ui.login(superuser)

    page = admin_ui.edit(covered_manual)

    assert page.fields["cover"].value == ("covers/front.png", "/media/covers/front.png")


def test_an_image_chosen_from_a_path_reads_as_its_name_without_a_link(admin_ui, superuser, diagram):
    admin_ui.login(superuser)
    page = admin_ui.create(Manual)

    page.fields["cover"].fill(diagram)

    assert page.fields["cover"].value == ("diagram.png", None)


@pytest.mark.parametrize("empty", [None, ""], ids=["None", "empty text"])
def test_an_empty_value_clears_the_stored_file_of_an_optional_field_once_saved(
    admin_ui, superuser, covered_manual, empty
):
    admin_ui.login(superuser)
    page = admin_ui.edit(covered_manual)

    page.fields["cover"].fill(empty)

    assert page.fields["cover"].value is None
    page.save()
    covered_manual.refresh_from_db()
    assert not covered_manual.cover


def test_a_file_chosen_after_clearing_replaces_the_stored_one_once_saved(
    admin_ui, superuser, covered_manual, diagram
):
    """Django rejects a form that uploads a file and clears the stored one at once, so
    choosing the file has to undo the clearing."""
    admin_ui.login(superuser)
    page = admin_ui.edit(covered_manual)
    page.fields["cover"].fill(None)

    page.fields["cover"].fill(diagram)

    assert page.fields["cover"].value == ("diagram.png", None)
    page.save()
    covered_manual.refresh_from_db()
    assert covered_manual.cover.name == "covers/diagram.png"


@pytest.mark.parametrize("empty", [None, ""], ids=["None", "empty text"])
def test_an_empty_value_cannot_empty_a_required_field_that_holds_a_stored_file(
    admin_ui, superuser, manual, empty
):
    admin_ui.login(superuser)
    page = admin_ui.edit(manual)

    with pytest.raises(ValueError) as failure:
        page.fields["file"].fill(empty)

    assert failure.value.args[0] == (
        "The field 'file' offers no Clear for the file it holds, so it cannot be emptied. "
        "The admin draws none for a required field."
    )
    assert page.fields["file"].value == ("manuals/assembly.txt", "/media/manuals/assembly.txt")


@pytest.mark.parametrize("empty", [None, ""], ids=["None", "empty text"])
def test_an_empty_value_drops_a_file_chosen_on_a_create_page(admin_ui, superuser, wiring, empty):
    admin_ui.login(superuser)
    page = admin_ui.create(Manual)
    page.fields["file"].fill(wiring)

    page.fields["file"].fill(empty)

    assert page.fields["file"].value is None


def test_a_file_filled_from_a_stored_file_reads_as_its_name_without_a_link(
    admin_ui, superuser, manual
):
    admin_ui.login(superuser)
    page = admin_ui.create(Manual)

    page.fields["file"].fill(manual.file)

    assert page.fields["file"].value == ("assembly.txt", None)


def test_a_file_filled_from_a_django_file_uploads_its_content_once_saved(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Manual)
    page.fields["title"].fill("Wiring")

    page.fields["file"].fill(ContentFile(WIRING, name="notes/wiring.txt"))

    assert page.fields["file"].value == ("wiring.txt", None)
    page.save()
    saved = Manual.objects.get(title="Wiring")
    assert saved.file.name == "manuals/wiring.txt"
    with saved.file.open("rb") as stored:
        assert stored.read() == WIRING


def test_a_django_file_without_a_name_cannot_fill_a_file_field(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Manual)

    with pytest.raises(ValueError) as failure:
        page.fields["file"].fill(ContentFile(WIRING))

    assert failure.value.args[0] == (
        "The field 'file' takes a file with a name to upload it under, and the ContentFile "
        "given has none."
    )


def test_populating_from_an_instance_uploads_its_stored_files_again_once_saved(
    admin_ui, superuser, covered_manual, diagram
):
    admin_ui.login(superuser)
    page = admin_ui.create(Manual)

    page.populate(covered_manual)
    page.save()

    copy = Manual.objects.exclude(pk=covered_manual.pk).get()
    assert copy.file.name != covered_manual.file.name
    with copy.file.open("rb") as stored:
        assert stored.read() == ASSEMBLY
    with copy.cover.open("rb") as stored:
        assert stored.read() == diagram.read_bytes()


def test_populating_from_an_instance_without_a_file_leaves_the_field_empty(
    admin_ui, superuser, manual
):
    admin_ui.login(superuser)
    page = admin_ui.create(Manual)

    page.populate(manual)

    assert page.fields["cover"].value is None


def test_a_file_chosen_on_a_create_page_reads_as_none_once_the_form_is_rejected(
    admin_ui, superuser, wiring
):
    admin_ui.login(superuser)
    page = admin_ui.create(Manual)
    page.fields["file"].fill(wiring)

    result = page.save()

    assert not result.success
    assert result.page.fields["file"].value is None


def test_a_file_chosen_on_an_edit_page_reads_as_the_stored_one_once_the_form_is_rejected(
    admin_ui, superuser, manual, wiring
):
    admin_ui.login(superuser)
    page = admin_ui.edit(manual)
    page.populate(title="", file=wiring)

    result = page.save()

    assert not result.success
    assert result.page.fields["file"].value == (
        "manuals/assembly.txt",
        "/media/manuals/assembly.txt",
    )


def test_a_cleared_file_reads_as_the_admin_renders_clear_once_the_form_is_rejected(
    admin_ui, superuser, covered_manual
):
    admin_ui.login(superuser)
    page = admin_ui.edit(covered_manual)
    page.populate(title="", cover=None)

    result = page.save()

    assert not result.success
    stored = ("covers/front.png", "/media/covers/front.png")
    assert result.page.fields["cover"].value == (None if KEEPS_CLEAR else stored)
