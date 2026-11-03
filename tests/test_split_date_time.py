"""The admin's split date-time: a date input and a time input for one date-time field,
read as the two texts and filled from a datetime, a pair or None."""

import datetime

import pytest

from project.shop.models import Feed

REFRESHED_AT = datetime.datetime(2026, 1, 15, 9, 30, tzinfo=datetime.timezone.utc)


@pytest.fixture
def refreshed_feed(db):
    return Feed.objects.create(source="refreshed.csv", refreshed_at=REFRESHED_AT)


def test_a_split_date_time_reads_as_its_date_and_time(admin_ui, superuser, refreshed_feed):
    admin_ui.login(superuser)

    page = admin_ui.edit(refreshed_feed)

    assert page.fields["refreshed_at"].value == ("2026-01-15", "09:30:00")


def test_an_empty_split_date_time_reads_as_two_empty_texts(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Feed)

    assert page.fields["refreshed_at"].value == ("", "")


def test_a_split_date_time_is_filled_from_a_datetime(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)

    page.fields["refreshed_at"].fill(datetime.datetime(2026, 11, 3, 11, 25, 48))

    assert page.fields["refreshed_at"].value == ("2026-11-03", "11:25:48")


def test_an_aware_datetime_is_typed_in_the_current_time_zone(admin_ui, superuser):
    """The test project's time zone is UTC."""
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)
    plus_two = datetime.timezone(datetime.timedelta(hours=2))

    page.fields["refreshed_at"].fill(datetime.datetime(2026, 1, 15, 9, 30, tzinfo=plus_two))

    assert page.fields["refreshed_at"].value == ("2026-01-15", "07:30:00")


def test_a_split_date_time_is_filled_from_its_own_value(admin_ui, superuser, refreshed_feed):
    admin_ui.login(superuser)
    value = admin_ui.edit(refreshed_feed).fields["refreshed_at"].value
    page = admin_ui.create(Feed)

    page.fields["refreshed_at"].fill(value)

    assert page.fields["refreshed_at"].value == ("2026-01-15", "09:30:00")


def test_a_split_date_time_is_filled_from_a_date_and_a_time(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)

    page.fields["refreshed_at"].fill((datetime.date(2026, 11, 3), datetime.time(11, 25, 48)))

    assert page.fields["refreshed_at"].value == ("2026-11-03", "11:25:48")


def test_a_split_date_time_is_filled_from_two_texts(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)

    page.fields["refreshed_at"].fill(("2026-11-03", "11:25:48"))

    assert page.fields["refreshed_at"].value == ("2026-11-03", "11:25:48")


def test_a_split_date_time_is_filled_from_a_date_and_a_text(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)

    page.fields["refreshed_at"].fill((datetime.date(2026, 11, 3), "11:25:48"))

    assert page.fields["refreshed_at"].value == ("2026-11-03", "11:25:48")


def test_a_split_date_time_is_filled_from_a_text_and_a_time(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)

    page.fields["refreshed_at"].fill(["2026-11-03", datetime.time(11, 25, 48)])

    assert page.fields["refreshed_at"].value == ("2026-11-03", "11:25:48")


def test_none_empties_a_split_date_time(admin_ui, superuser, refreshed_feed):
    admin_ui.login(superuser)
    page = admin_ui.edit(refreshed_feed)

    page.fields["refreshed_at"].fill(None)

    assert page.fields["refreshed_at"].value == ("", "")


@pytest.mark.parametrize("empty", [None, ""], ids=["none", "empty text"])
def test_an_empty_date_empties_only_the_date(admin_ui, superuser, refreshed_feed, empty):
    admin_ui.login(superuser)
    page = admin_ui.edit(refreshed_feed)

    page.fields["refreshed_at"].fill((empty, "11:25:48"))

    assert page.fields["refreshed_at"].value == ("", "11:25:48")


@pytest.mark.parametrize("empty", [None, ""], ids=["none", "empty text"])
def test_an_empty_time_empties_only_the_time(admin_ui, superuser, refreshed_feed, empty):
    admin_ui.login(superuser)
    page = admin_ui.edit(refreshed_feed)

    page.fields["refreshed_at"].fill(("2026-11-03", empty))

    assert page.fields["refreshed_at"].value == ("2026-11-03", "")


@pytest.mark.parametrize(
    "value",
    [
        "2026-11-03 11:25:48",
        datetime.date(2026, 11, 3),
        ("2026-11-03",),
        ("2026-11-03", "11:25:48", "UTC"),
        (datetime.time(11, 25, 48), datetime.date(2026, 11, 3)),
        (REFRESHED_AT, "11:25:48"),
    ],
    ids=["text", "date", "one item", "three items", "swapped", "datetime for the date"],
)
def test_a_value_that_is_no_date_time_is_refused(admin_ui, superuser, value):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)

    with pytest.raises(TypeError) as failure:
        page.fields["refreshed_at"].fill(value)

    assert str(failure.value) == (
        f"The field 'refreshed_at' takes a datetime, a (date, time) pair or None, "
        f"not {value!r}. Each half of the pair is a date or time, text, or None."
    )


def test_a_saved_split_date_time_is_stored(admin_ui, superuser):
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)
    page.populate(source="catalog.csv", refreshed_at=REFRESHED_AT)

    assert page.save().success

    assert Feed.objects.get().refreshed_at == REFRESHED_AT


@pytest.mark.parametrize(
    "value, error, typed",
    [
        (("soon", "11:25:48"), "Enter a valid date.", ("soon", "11:25:48")),
        (("2026-11-03", "soon"), "Enter a valid time.", ("2026-11-03", "soon")),
        ((None, "11:25:48"), "Enter a valid date.", ("", "11:25:48")),
        (("2026-11-03", None), "Enter a valid time.", ("2026-11-03", "")),
    ],
    ids=["invalid date", "invalid time", "time without a date", "date without a time"],
)
def test_the_admin_error_is_reported_under_the_field(admin_ui, superuser, value, error, typed):
    """The rejected page still shows what was typed."""
    admin_ui.login(superuser)
    page = admin_ui.create(Feed)
    page.populate(source="catalog.csv", refreshed_at=value)

    result = page.save()

    assert not result.success
    assert result.page.fields["refreshed_at"].errors == [error]
    assert result.page.fields["refreshed_at"].value == typed


def test_a_split_date_time_offers_no_choices(admin_ui, superuser):
    admin_ui.login(superuser)

    page = admin_ui.create(Feed)

    assert page.fields["refreshed_at"].choices == []
