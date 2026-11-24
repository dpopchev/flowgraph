"""The names of the buckets a configuration shows: each bucket of the configuration is its name."""

import pytest

from flowgraph.record.listing import Bucket, WatchShows
from flowgraph.status.buckets import (
    BACKLOG_BUCKET,
    COMPLETED_BUCKET,
    IN_PROGRESS_BUCKET,
    REMOVED_BUCKET,
    shown_buckets,
)

pytestmark = pytest.mark.view


def test_the_two_buckets_named_are_the_two_names() -> None:
    shows = WatchShows((Bucket.BACKLOG, Bucket.IN_PROGRESS))
    assert shown_buckets(shows) == {BACKLOG_BUCKET, IN_PROGRESS_BUCKET}


def test_the_four_buckets_named_are_the_four_names() -> None:
    shows = WatchShows(tuple(Bucket))
    assert shown_buckets(shows) == {
        BACKLOG_BUCKET,
        IN_PROGRESS_BUCKET,
        COMPLETED_BUCKET,
        REMOVED_BUCKET,
    }
