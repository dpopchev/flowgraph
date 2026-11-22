"""A no of fgraph verify by id: what it says, where its Bug is added, one write or none."""

from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.bug import BUG
from flowgraph.criterion import NO_COMMIT, make_scenario
from flowgraph.development.scope import OutOfScopeError
from flowgraph.feature import FeatureState, completed_feature, make_feature, started_feature
from flowgraph.item.commands import Written
from flowgraph.item.verify import verify_item_no
from flowgraph.parent import STANDALONE, FeatureId, Parent, make_feature_id
from flowgraph.record.store import FeatureStore, Store
from flowgraph.story import make_story_id
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    WorkItemState,
    append_task,
    completed_task,
    completed_work_item,
    make_work_item,
    started_task,
    started_work_item,
)

pytestmark = pytest.mark.command

ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
TEXT = "status listed no reason"
F1 = make_feature_id(1)
FEATURE = make_feature(F1, "a feature title", ["a criterion"], "", ON)
STARTED = started_feature(FEATURE, ON)
COMPLETED = completed_feature(STARTED, ON, NO_COMMIT)


def never(*_: object) -> Never:
    """A read or a write of the record that a verify never asks for."""
    raise AssertionError("a verify reads the work item, its Feature and the Bugs, and saves")


def story(parent: Parent) -> WorkItemState:
    """The Story S-0001 under that parent, completed with its one Task."""
    criterion = make_scenario("a state", "an action", "another")
    made = make_work_item(make_story_id(1), "a title", criterion, "", ON, parent)
    task = make_task(make_task_id(1), "a task title", "an output", "", ON)
    begun = started_task(started_work_item(append_task(made, task), ON), make_task_id(1), ON)
    return completed_work_item(completed_task(begun, make_task_id(1), ON, NO_COMMIT), ON, NO_COMMIT)


class Record:
    """A record of the Story S-0001 and the Feature F-0001: what it saved and how often it was
    put back; with `refuse_story` the save of the Story is refused, as out of the scope of a
    branch."""

    def __init__(self, item: WorkItemState, feature: FeatureState, refuse_story: bool = False):
        self.saved: list[WorkItemState] = []
        self.restored = 0
        self.held = {item.id: item}
        self.feature = feature
        self.refuse_story = refuse_story

    def save_work_item(self, item: WorkItemState) -> None:
        if self.refuse_story and item.id == make_story_id(1):
            raise OutOfScopeError("S-0001 is not written here")
        self.saved.append(item)

    def load_feature(self, feature_id: FeatureId) -> FeatureState:
        return self.feature

    def restore(self) -> None:
        self.restored += 1

    def store(self) -> Store:
        """The store of the record."""
        return Store(
            find_work_item_rows=lambda kind: [],
            load_work_item=self.held.__getitem__,
            find_work_item_detail=never,
            find_task_ids=never,
            save_work_item=self.save_work_item,
            load_queue=never,
            save_queue=never,
            find_changed_files=never,
            restore_files=self.restore,
            features=FeatureStore(self.load_feature, never, lambda: ["F-0001"]),
        )


def verify(record: Record) -> Written:
    """A no on S-0001 of the record."""
    return verify_item_no("S-0001", TEXT, record.store(), lambda: ON)


def test_a_no_names_the_work_item_and_the_bug_it_adds() -> None:
    written = verify(Record(story(STANDALONE), STARTED))
    assert written.out == "verified S-0001 no\nadded B-0001 amending S-0001\n"


def test_the_message_of_its_commit_names_the_verify_and_the_add() -> None:
    written = verify(Record(story(STANDALONE), STARTED))
    assert written.message == "chore: verify S-0001 no and add B-0001 in the record"


def test_the_bug_of_a_work_item_under_a_feature_not_completed_joins_that_feature() -> None:
    record = Record(story(F1), STARTED)
    verify(record)
    assert record.saved[0].parent == F1


def test_the_bug_of_a_work_item_under_a_completed_feature_stands_alone() -> None:
    record = Record(story(F1), COMPLETED)
    verify(record)
    assert record.saved[0].parent == STANDALONE


def test_a_save_refused_after_the_bug_is_saved_puts_every_file_back() -> None:
    record = Record(story(STANDALONE), STARTED, refuse_story=True)
    with pytest.raises(OutOfScopeError):
        verify(record)
    assert record.restored == 1


def test_the_bug_is_of_the_kind_bug() -> None:
    record = Record(story(STANDALONE), STARTED)
    verify(record)
    assert record.saved[0].id.kind == BUG
