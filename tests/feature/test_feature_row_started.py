"""The row of a Feature tells a started Feature from one never started that InProgress lists."""

from datetime import UTC, datetime

import pytest

from flowgraph.feature import (
    blocked_feature,
    feature_row,
    make_feature,
    started_feature,
)
from flowgraph.parent import make_feature_id

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
FEATURE = make_feature(make_feature_id(1), "a title", ["a criterion"], "", CREATED)
STARTED = started_feature(FEATURE, CREATED)


def test_the_row_of_a_started_feature_is_started() -> None:
    assert feature_row(STARTED, ["started", "backlog"]).is_started


def test_the_row_of_a_feature_never_started_is_not_started_in_progress_as_it_is() -> None:
    assert not feature_row(FEATURE, ["started", "backlog"]).is_started


def test_the_row_of_a_blocked_feature_is_not_started() -> None:
    blocked = blocked_feature(STARTED, "a reason", "the developer", CREATED)
    assert not feature_row(blocked, ["started", "backlog"]).is_started
