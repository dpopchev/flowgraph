"""The row of a Feature: its id, its title, its bucket and its work items completed."""

from datetime import UTC, datetime

import pytest

from flowgraph.feature import FeatureRow, feature_row, make_feature, started_feature
from flowgraph.parent import make_feature_id

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
FEATURE = make_feature(make_feature_id(1), "a title", ["a criterion"], "", CREATED)
STARTED = started_feature(FEATURE, CREATED)


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
    [[], ["backlog", "backlog"], ["started", "backlog"], ["completed", "backlog"]],
    ids=["none", "none-begun", "one-started", "one-completed"],
)
def test_the_row_of_a_started_feature_is_in_progress_whatever_its_work_items_not_all_done(
    states: list[str],
) -> None:
    assert feature_row(STARTED, states).bucket == "InProgress"


def test_the_row_of_a_started_feature_whose_work_items_are_all_done_is_derived_completed() -> None:
    assert feature_row(STARTED, ["completed", "removed"]).bucket == "Completed"
