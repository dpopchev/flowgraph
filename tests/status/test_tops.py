"""The tops of status: how many items each bucket lists and what the flags of a command ask."""

import pytest

from flowgraph.record.config import make_config
from flowgraph.record.listing import ALL_LINES, Lines, StatusLists
from flowgraph.status.buckets import (
    BACKLOG_BUCKET,
    COMPLETED_BUCKET,
    IN_PROGRESS_BUCKET,
    REMOVED_BUCKET,
)
from flowgraph.status.tops import WHOLE, Tops, same_top, top_of, tops_asked, tops_of

pytestmark = pytest.mark.view


def test_the_same_top_is_the_top_of_every_bucket() -> None:
    assert same_top(2) == Tops(2, 2, 2, 2)


def test_the_same_top_of_none_is_the_whole() -> None:
    assert same_top(None) == WHOLE


CONFIGURED = Tops(2, 4, 3, 5)


def test_the_lines_the_configuration_sets_are_the_tops() -> None:
    lists = StatusLists(Lines(2), ALL_LINES, Lines(3), Lines(5))
    assert tops_of(lists) == Tops(2, None, 3, 5)


def test_the_defaults_of_the_configuration_are_one_all_five_and_five() -> None:
    assert tops_of(make_config("").status) == Tops(1, None, 5, 5)


def test_no_flag_asks_the_tops_the_configuration_sets() -> None:
    assert tops_asked(CONFIGURED, every=False, backlog=False) == CONFIGURED


def test_the_flag_of_the_backlog_asks_it_whole_and_the_others_as_configured() -> None:
    assert tops_asked(CONFIGURED, every=False, backlog=True) == Tops(None, 4, 3, 5)


@pytest.mark.parametrize("backlog", [False, True])
def test_every_asks_the_whole_whatever_the_flag_of_the_backlog(backlog: bool) -> None:
    assert tops_asked(CONFIGURED, every=True, backlog=backlog) == WHOLE


@pytest.mark.parametrize(
    ("name", "top"),
    [
        (BACKLOG_BUCKET, 1),
        (IN_PROGRESS_BUCKET, 2),
        (COMPLETED_BUCKET, 3),
        (REMOVED_BUCKET, 4),
    ],
)
def test_the_top_of_a_bucket_is_its_field(name: str, top: int) -> None:
    assert top_of(Tops(1, 2, 3, 4), name) == top


def test_the_top_of_a_name_that_is_no_bucket_raises() -> None:
    with pytest.raises(KeyError):
        top_of(Tops(1, 2, 3, 4), "Other")
