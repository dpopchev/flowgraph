"""A Feature named by its id: its add, its view over its work items, and the parent it gives."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.criterion import NO_COMMIT, make_commit
from flowgraph.feature import (
    FeatureNotFoundError,
    FeatureState,
    completed_feature,
    make_feature,
    started_feature,
)
from flowgraph.feature_item import add_feature_item, parent_named, show_feature_item
from flowgraph.item import Written
from flowgraph.parent import STANDALONE, FeatureId, FeatureIdError, make_feature_id
from flowgraph.queue import Queue, make_queue
from flowgraph.scope import OutOfScopeError, Scope, within
from flowgraph.store import NO_FEATURES, FeatureStore, Store
from flowgraph.story import STORY, make_story_id
from flowgraph.task import CompletedAlreadyError
from flowgraph.upkeep import UPKEEP, make_upkeep_id
from flowgraph.work_item import Kind, WorkItemRow

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
ONE = make_feature_id(1)
FEATURE = make_feature(ONE, "a feature title", ["a criterion", "another"], "why", CREATED)
LANDED = completed_feature(started_feature(FEATURE, CREATED), CREATED, make_commit("abc1234"))
ROWS = {
    STORY: [
        WorkItemRow("S-0001", "a story", "started", parent="F-0001", created=CREATED),
        WorkItemRow("S-0002", "a story alone", "backlog", created=CREATED),
        WorkItemRow("S-0003", "a later story", "backlog", parent="F-0001", created=CREATED),
    ],
    UPKEEP: [WorkItemRow("U-0001", "an upkeep", "backlog", parent="F-0001", created=CREATED)],
}
NO_QUEUE = make_queue([])


def never(*_: object) -> Never:
    """A read or a write of the record that a Feature never asks for."""
    raise AssertionError("a Feature reads the rows of the work items, the queue and its own file")


def store(
    saved: list[FeatureState] | None = None,
    queue: Queue = NO_QUEUE,
    feature: FeatureState = FEATURE,
    rows: Mapping[Kind, list[WorkItemRow]] = ROWS,
) -> Store:
    """The store of a record holding that Feature as F-0001, those rows and that queue.

    It holds FEATURE and ROWS unless others are given, and notes a Feature it saves.
    """
    kept = [] if saved is None else saved

    def held(feature_id: FeatureId) -> FeatureState:
        if feature_id != ONE:
            raise FeatureNotFoundError(feature_id)
        return feature

    return Store(
        find_work_item_rows=lambda kind: rows.get(kind, []),
        load_work_item=never,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=never,
        load_queue=lambda: queue,
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
    saved: list[FeatureState] = []
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
        "Work items (3)\n"
        "  S-0001  a story  InProgress\n"
        "  S-0003  a later story  Backlog\n"
        "  U-0001  an upkeep  Backlog\n"
    )


@pytest.mark.view
def test_the_work_items_in_backlog_of_a_feature_are_shown_in_the_order_the_queue_gives() -> None:
    placed = make_queue([make_upkeep_id(1), make_story_id(2), make_story_id(3)])
    assert show_feature_item("F-0001", store(queue=placed)).splitlines()[-3:] == [
        "  S-0001  a story  InProgress",
        "  U-0001  an upkeep  Backlog",
        "  S-0003  a later story  Backlog",
    ]


@pytest.mark.view
def test_a_started_feature_is_shown_in_progress_though_no_work_item_of_it_is_begun() -> None:
    started = started_feature(FEATURE, CREATED)
    shown = show_feature_item("F-0001", store(feature=started, rows={UPKEEP: ROWS[UPKEEP]}))
    assert shown.splitlines()[1] == "  bucket       InProgress"


@pytest.mark.view
def test_a_completed_feature_is_shown_completed_with_its_commit_under_its_bucket() -> None:
    shown = show_feature_item("F-0001", store(feature=LANDED))
    assert shown.splitlines()[1:3] == ["  bucket       Completed", "  commit       abc1234"]


@pytest.mark.view
def test_a_feature_completed_without_a_commit_is_shown_without_one() -> None:
    unproven = completed_feature(started_feature(FEATURE, CREATED), CREATED, NO_COMMIT)
    shown = show_feature_item("F-0001", store(feature=unproven))
    assert shown.splitlines()[1:3] == ["  bucket       Completed", "  description  why"]


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
def test_a_work_item_added_under_a_started_feature_takes_it_as_parent() -> None:
    assert parent_named("F-0001", store(feature=started_feature(FEATURE, CREATED))) == ONE


@pytest.mark.command
def test_a_work_item_added_under_a_completed_feature_is_refused() -> None:
    with pytest.raises(CompletedAlreadyError, match=r"^F-0001 is completed already$"):
        parent_named("F-0001", store(feature=LANDED))


@pytest.mark.command
def test_a_parent_the_record_does_not_hold_is_refused() -> None:
    with pytest.raises(FeatureNotFoundError, match=r"^no Feature F-0009 in the record$"):
        parent_named("F-0009", store())


@pytest.mark.command
def test_a_parent_that_is_no_feature_id_is_refused() -> None:
    with pytest.raises(FeatureIdError, match=r"^'S-0001' is no Feature id: it is F- and a number$"):
        parent_named("S-0001", store())


@pytest.mark.command
def test_a_store_built_without_features_holds_none() -> None:
    with pytest.raises(FeatureNotFoundError, match=r"^no Feature F-0001 in the record$"):
        NO_FEATURES.load_feature(ONE)


@pytest.mark.command
def test_a_feature_is_not_written_on_the_branch_of_a_work_item() -> None:
    scope = Scope("wi/S-0001-a-slug", make_story_id(1))
    with pytest.raises(
        OutOfScopeError,
        match=r"^F-0001 is not written here: the branch wi/S-0001-a-slug writes S-0001 alone$",
    ):
        within(store(), lambda: scope, never).features.save_feature(FEATURE)


@pytest.mark.command
def test_a_feature_is_written_on_a_branch_no_work_item_owns() -> None:
    saved: list[FeatureState] = []
    within(store(saved), lambda: None, never).features.save_feature(FEATURE)
    assert saved == [FEATURE]
