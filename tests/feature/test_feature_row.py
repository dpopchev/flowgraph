"""The row of a Feature: its id, its title, its bucket and its work items completed."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import NO_COMMIT, make_commit
from flowgraph.feature import (
    FeatureRow,
    FeatureState,
    completed_feature,
    feature_row,
    make_feature,
    started_feature,
)
from flowgraph.parent import make_feature_id

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
FEATURE = make_feature(make_feature_id(1), "a title", ["a criterion"], "", CREATED)
STARTED = started_feature(FEATURE, CREATED)
COMPLETED = completed_feature(STARTED, CREATED, NO_COMMIT)


def test_the_row_of_a_feature_names_its_id_its_title_and_its_derived_bucket() -> None:
    assert feature_row(FEATURE, ["started", "backlog"]) == FeatureRow(
        "F-0001", "a title", "InProgress", completed=0, held=2
    )


def test_the_row_of_a_feature_counts_its_work_items_completed() -> None:
    assert feature_row(FEATURE, ["completed", "started", "completed"]).completed == 2


def test_the_row_of_a_feature_holds_no_removed_work_item() -> None:
    assert feature_row(FEATURE, ["completed", "backlog", "removed"]).held == 2


def test_the_row_of_a_feature_without_a_work_item_is_in_backlog() -> None:
    assert feature_row(FEATURE, []).bucket == "Backlog"


@pytest.mark.parametrize(
    "states",
    [
        [],
        ["backlog", "backlog"],
        ["started", "backlog"],
        ["completed", "backlog"],
        ["completed", "removed"],
    ],
    ids=["none", "none-begun", "one-started", "one-completed", "all-completed-or-removed"],
)
def test_the_row_of_a_started_feature_is_in_progress_whatever_its_work_items(
    states: list[str],
) -> None:
    assert feature_row(STARTED, states).bucket == "InProgress"


def test_the_row_of_a_completed_feature_is_in_completed_by_its_own_state() -> None:
    assert feature_row(COMPLETED, ["completed", "backlog"]).bucket == "Completed"


def test_the_row_of_a_feature_completed_in_a_commit_holds_its_sha() -> None:
    landed = completed_feature(STARTED, CREATED, make_commit("abc1234"))
    assert feature_row(landed, ["completed"]).commit == "abc1234"


@pytest.mark.parametrize(
    "feature", [FEATURE, STARTED, COMPLETED], ids=["in-backlog", "started", "without-a-commit"]
)
def test_the_row_of_a_feature_that_has_no_commit_holds_none(feature: FeatureState) -> None:
    assert feature_row(feature, ["completed"]).commit == ""
