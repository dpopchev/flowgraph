"""The tops of status: how many items each bucket lists and what the flags of a command ask."""

import pytest

from flowgraph.status.buckets import (
    BACKLOG_BUCKET,
    COMPLETED_BUCKET,
    IN_PROGRESS_BUCKET,
    REMOVED_BUCKET,
)
from flowgraph.status.tops import WHOLE, Tops, same_top, top_of, tops_asked

pytestmark = pytest.mark.view


def test_the_same_top_is_the_top_of_every_bucket() -> None:
    assert same_top(2) == Tops(2, 2, 2, 2)


def test_the_same_top_of_none_is_the_whole() -> None:
    assert same_top(None) == WHOLE


def test_no_flag_asks_the_first_line_of_the_backlog_and_five_of_each_other() -> None:
    assert tops_asked(every=False, backlog=False) == Tops(
        backlog=1, in_progress=5, completed=5, removed=5
    )


def test_the_flag_of_the_backlog_asks_it_whole_and_the_others_short() -> None:
    assert tops_asked(every=False, backlog=True) == Tops(None, 5, 5, 5)


@pytest.mark.parametrize("backlog", [False, True])
def test_every_asks_the_whole_whatever_the_flag_of_the_backlog(backlog: bool) -> None:
    assert tops_asked(every=True, backlog=backlog) == WHOLE


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
