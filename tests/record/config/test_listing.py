"""The lines each bucket lists and the buckets a frame shows: `[status]` and `[watch]`."""

import pytest

from flowgraph.record.config import ConfigError, make_config
from flowgraph.record.listing import (
    ALL_LINES,
    Bucket,
    Lines,
    StatusLists,
    WatchShows,
    buckets_text,
    listed_text,
)

pytestmark = pytest.mark.edge

TAKES_LINES = "it takes a count of lines of 1 or more, or all"
TAKES_BUCKETS = (
    "it takes the buckets to show, among backlog, in-progress, completed and removed,"
    " separated by commas"
)
EVERY_BUCKET = (Bucket.BACKLOG, Bucket.IN_PROGRESS, Bucket.COMPLETED, Bucket.REMOVED)


def test_a_configuration_without_the_tables_lists_one_all_five_and_five_lines() -> None:
    assert make_config("").status == StatusLists(Lines(1), ALL_LINES, Lines(5), Lines(5))


def test_a_configuration_without_the_tables_shows_every_bucket() -> None:
    assert make_config("").watch == WatchShows(EVERY_BUCKET)


def test_each_key_of_status_is_read_as_a_count() -> None:
    text = "[status]\nbacklog = 2\nin-progress = 3\ncompleted = 4\nremoved = 6\n"
    assert make_config(text).status == StatusLists(Lines(2), Lines(3), Lines(4), Lines(6))


def test_each_key_of_status_is_read_as_all() -> None:
    text = '[status]\nbacklog = "all"\nin-progress = "all"\ncompleted = "all"\nremoved = "all"\n'
    assert make_config(text).status == StatusLists(ALL_LINES, ALL_LINES, ALL_LINES, ALL_LINES)


@pytest.mark.parametrize(
    ("value", "written"),
    [("0", "0"), ("-1", "-1"), ('"many"', '"many"'), ("true", "true"), ("2.5", "2.5")],
)
def test_a_count_that_is_no_count_of_lines_is_refused_with_the_whole_line(
    value: str, written: str
) -> None:
    with pytest.raises(ConfigError) as error:
        make_config(f"[status]\nbacklog = {value}\n")
    assert str(error.value) == f"status.backlog is {written}: {TAKES_LINES}"


def test_in_progress_with_an_underscore_is_refused_as_no_key() -> None:
    with pytest.raises(ConfigError) as error:
        make_config("[status]\nin_progress = 2\n")
    assert str(error.value) == "status.in_progress is no key of the configuration"


def test_a_count_of_lines_refused_under_in_progress_names_the_dashed_key() -> None:
    with pytest.raises(ConfigError) as error:
        make_config("[status]\nin-progress = 0\n")
    assert str(error.value) == f"status.in-progress is 0: {TAKES_LINES}"


def test_a_status_that_is_no_table_is_refused() -> None:
    with pytest.raises(ConfigError) as error:
        make_config("status = 3\n")
    assert str(error.value) == "status is 3: it takes a table"


def test_the_buckets_are_read_in_the_order_of_the_flow() -> None:
    text = '[watch]\nbuckets = "removed, in-progress, backlog"\n'
    assert make_config(text).watch == WatchShows(
        (Bucket.BACKLOG, Bucket.IN_PROGRESS, Bucket.REMOVED)
    )


@pytest.mark.parametrize(
    ("value", "written"),
    [
        ('""', '""'),
        ('"backlog, done"', '"backlog, done"'),
        ('"backlog, backlog"', '"backlog, backlog"'),
        ("3", "3"),
        ('["backlog"]', '["backlog"]'),
    ],
)
def test_buckets_that_are_no_buckets_are_refused_with_the_whole_line(
    value: str, written: str
) -> None:
    with pytest.raises(ConfigError) as error:
        make_config(f"[watch]\nbuckets = {value}\n")
    assert str(error.value) == f"watch.buckets is {written}: {TAKES_BUCKETS}"


def test_a_count_of_lines_is_written_as_its_number() -> None:
    assert listed_text(Lines(3)) == 3


def test_all_lines_are_written_as_all() -> None:
    assert listed_text(ALL_LINES) == "all"


def test_the_buckets_are_written_joined_by_a_comma_and_a_blank() -> None:
    assert buckets_text(WatchShows((Bucket.BACKLOG, Bucket.REMOVED))) == "backlog, removed"
