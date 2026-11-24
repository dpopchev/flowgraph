"""The detail of a work item read whole holds the text of the criterion it realizes."""

from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.feature import FeatureNotFoundError, FeatureState, make_feature
from flowgraph.parent import FeatureId, make_feature_id
from flowgraph.record.store import FeatureStore, Store
from flowgraph.relation.depends import bucketed
from flowgraph.work_item import WorkItemDetail

pytestmark = pytest.mark.view

ONE = make_feature_id(1)
FEATURE = make_feature(
    ONE,
    "a feature title",
    ["a first criterion", "a second criterion"],
    "",
    datetime(2026, 1, 1, tzinfo=UTC),
)


def never(*_: object) -> Never:
    """A read or a write of the record that the view never asks for."""
    raise AssertionError("the view reads the rows of the work items and the Features")


def held(feature_id: FeatureId) -> FeatureState:
    """The record of one Feature, F-0001."""
    if feature_id != ONE:
        raise FeatureNotFoundError(feature_id)
    return FEATURE


def store() -> Store:
    """A store whose record holds F-0001 and no work item row."""
    return Store(
        find_work_item_rows=lambda _: [],
        load_work_item=never,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=never,
        load_queue=never,
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
        features=FeatureStore(held, never, list),
    )


def detail(parent: str, realizes: int | None) -> WorkItemDetail:
    """The detail of S-0001 under that parent, naming that criterion."""
    return WorkItemDetail("S-0001", "a title", "backlog", "", [], parent=parent, realizes=realizes)


def test_the_detail_of_a_work_item_realizing_the_second_criterion_holds_its_text() -> None:
    assert bucketed(detail("F-0001", 2), store()).realized == "a second criterion"


def test_the_detail_of_a_work_item_naming_no_criterion_is_as_it_was_given() -> None:
    given = detail("F-0001", None)
    assert bucketed(given, store()) == given
