"""The row of a Feature: its id, its title and the bucket derived from its work items."""

from datetime import UTC, datetime

import pytest

from flowgraph.feature import FeatureRow, feature_row, make_feature
from flowgraph.parent import make_feature_id

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
FEATURE = make_feature(make_feature_id(1), "a title", ["a criterion"], "", CREATED)


def test_the_row_of_a_feature_names_its_id_its_title_and_its_derived_bucket() -> None:
    assert feature_row(FEATURE, ["started", "backlog"]) == FeatureRow(
        "F-0001", "a title", "InProgress"
    )


def test_the_row_of_a_feature_without_a_work_item_is_in_backlog() -> None:
    assert feature_row(FEATURE, []).bucket == "Backlog"
