"""A Feature named by its id: its add, its view over its work items, and the parent it gives."""

from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.feature import Feature, FeatureNotFoundError, make_feature
from flowgraph.feature_item import add_feature_item, parent_named, show_feature_item
from flowgraph.item import Written
from flowgraph.parent import STANDALONE, FeatureId, FeatureIdError, make_feature_id
from flowgraph.scope import OutOfScopeError, Scope, within
from flowgraph.store import NO_FEATURES, FeatureStore, Store
from flowgraph.story import STORY, make_story_id
from flowgraph.upkeep import UPKEEP
from flowgraph.work_item import WorkItemRow

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
ONE = make_feature_id(1)
FEATURE = make_feature(ONE, "a feature title", ["a criterion", "another"], "why", CREATED)
ROWS = {
    STORY: [
        WorkItemRow("ST-0001", "a story", "started", parent="F-0001", created=CREATED),
        WorkItemRow("ST-0002", "a story alone", "backlog", created=CREATED),
    ],
    UPKEEP: [WorkItemRow("U-0001", "an upkeep", "backlog", parent="F-0001", created=CREATED)],
}


def never(*_: object) -> Never:
    """A read or a write of the record that a Feature never asks for."""
    raise AssertionError("a Feature reads the rows of the work items and its own file alone")


def held(feature_id: FeatureId) -> Feature:
    """The Feature of that id among those the record holds, which is FEATURE alone."""
    if feature_id != ONE:
        raise FeatureNotFoundError(feature_id)
    return FEATURE


def store(saved: list[Feature] | None = None) -> Store:
    """The store of a record holding FEATURE and ROWS; it notes the Features it saves."""
    kept = [] if saved is None else saved
    return Store(
        find_work_item_rows=lambda kind: ROWS.get(kind, []),
        load_work_item=never,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=never,
        load_queue=never,
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
        features=FeatureStore(held, kept.append, lambda: ["F-0001"]),
    )


@pytest.mark.command
def test_a_feature_added_says_its_id_and_the_message_of_its_commit() -> None:
    added = add_feature_item("a title", ["a criterion"], "", store(), lambda: CREATED)
    assert added == Written("added F-0002\n", "chore: add F-0002 in the record")


@pytest.mark.command
def test_a_feature_added_is_saved_under_the_next_free_id() -> None:
    saved: list[Feature] = []
    add_feature_item("a title", ["a criterion"], "", store(saved), lambda: CREATED)
    assert saved == [make_feature(make_feature_id(2), "a title", ["a criterion"], "", CREATED)]


@pytest.mark.view
def test_a_feature_is_shown_with_its_criteria_and_its_work_items_by_bucket() -> None:
    assert show_feature_item("F-0001", store()) == (
        "F-0001  a feature title\n"
        "  bucket       InProgress\n"
        "  description  why\n"
        "Criteria (2)\n"
        "  a criterion\n"
        "  another\n"
        "Work items (2)\n"
        "  ST-0001  a story  InProgress\n"
        "  U-0001  an upkeep  Backlog\n"
    )


@pytest.mark.view
def test_a_feature_the_record_does_not_hold_is_not_shown() -> None:
    with pytest.raises(FeatureNotFoundError, match=r"^no Feature F-0009 in the record$"):
        show_feature_item("F-0009", store())


@pytest.mark.command
def test_a_work_item_added_without_a_parent_stands_alone() -> None:
    assert parent_named(None, store()) == STANDALONE


@pytest.mark.command
def test_a_work_item_added_under_a_feature_the_record_holds_takes_it_as_parent() -> None:
    assert parent_named("F-0001", store()) == ONE


@pytest.mark.command
def test_a_parent_the_record_does_not_hold_is_refused() -> None:
    with pytest.raises(FeatureNotFoundError, match=r"^no Feature F-0009 in the record$"):
        parent_named("F-0009", store())


@pytest.mark.command
def test_a_parent_that_is_no_feature_id_is_refused() -> None:
    with pytest.raises(
        FeatureIdError, match=r"^'ST-0001' is no Feature id: it is F- and a number$"
    ):
        parent_named("ST-0001", store())


@pytest.mark.command
def test_a_store_built_without_features_holds_none() -> None:
    with pytest.raises(FeatureNotFoundError, match=r"^no Feature F-0001 in the record$"):
        NO_FEATURES.load_feature(ONE)


@pytest.mark.command
def test_a_feature_is_not_written_on_the_branch_of_a_work_item() -> None:
    scope = Scope("wi/ST-0001-a-slug", make_story_id(1))
    with pytest.raises(
        OutOfScopeError,
        match=r"^F-0001 is not written here: the branch wi/ST-0001-a-slug writes ST-0001 alone$",
    ):
        within(store(), lambda: scope, never).features.save_feature(FEATURE)


@pytest.mark.command
def test_a_feature_is_written_on_a_branch_no_work_item_owns() -> None:
    saved: list[Feature] = []
    within(store(saved), lambda: None, never).features.save_feature(FEATURE)
    assert saved == [FEATURE]
