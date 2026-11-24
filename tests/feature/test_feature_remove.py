"""The remove of a Feature: one in Backlog is removed with its reason, its work items with it."""

import tomllib
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Never

import pytest

from flowgraph.criterion import NO_COMMIT, EmptyPartError, make_scenario
from flowgraph.development.scope import OutOfScopeError, Scope, within
from flowgraph.feature import (
    FeatureFileError,
    FeatureNotFoundError,
    FeatureRow,
    FeatureState,
    RemovedFeature,
    blocked_feature,
    completed_feature,
    feature_detail,
    feature_row,
    make_feature,
    noted_feature,
    read_feature,
    removed_feature,
    started_feature,
    unblocked_feature,
    write_feature,
)
from flowgraph.feature.amend import FeatureAmendment, amended_feature
from flowgraph.feature.item import parent_named, show_feature_item
from flowgraph.feature.move import check_move
from flowgraph.feature.remove import remove_named
from flowgraph.feature.start import check_start_under_feature
from flowgraph.item.commands import Written
from flowgraph.knowledge import FINDING, make_knowledge_line
from flowgraph.parent import STANDALONE, FeatureId, Parent, make_feature_id
from flowgraph.record.queue import make_queue
from flowgraph.record.store import FeatureStore, Store
from flowgraph.relation import RelationError
from flowgraph.status import status_text
from flowgraph.story import STORY, make_story_id
from flowgraph.task import (
    BlockedError,
    CompletedAlreadyError,
    NotBlockedError,
    StartedAlreadyError,
    make_task,
    make_task_id,
)
from flowgraph.work_item import (
    RemovedAlreadyError,
    WorkItem,
    WorkItemState,
    append_task,
    blocked_work_item,
    completed_task,
    completed_work_item,
    make_work_item,
    removed_task,
    removed_work_item,
    started_task,
    started_work_item,
    work_item_row,
)

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
BEGUN = datetime(2026, 1, 2, 8, 0, 0, tzinfo=UTC)
ON = datetime(2026, 1, 3, 9, 0, 0, 500, tzinfo=UTC)
REASON = "filed by mistake"
ONE = make_feature_id(1)
S2 = make_story_id(2)
FEATURE = make_feature(ONE, "a title", ["a criterion", "another"], "why", CREATED)
STARTED = started_feature(FEATURE, BEGUN)
BLOCKED = blocked_feature(STARTED, "a reason", "someone", BEGUN)
COMPLETED = completed_feature(STARTED, BEGUN, NO_COMMIT)
GONE = removed_feature(FEATURE, REASON, ON)
NOTED = noted_feature(
    make_feature(ONE, "a title", ["a criterion"], "why", CREATED, ("lane",)),
    make_knowledge_line(FINDING, "a text", CREATED),
)
FILE = Path("items") / "F-0001.toml"
WRITTEN_BEFORE = (
    'id = "F-0001"\ntitle = "a title"\ncreated = 2026-01-01 12:30:15+00:00\n'
    'criteria = ["a criterion"]\n'
)
REMOVED_ALREADY = r"^F-0001 is removed already$"


def blocked_in_progress(feature: FeatureState, on: datetime) -> FeatureState:
    """The Feature started and then blocked."""
    return blocked_feature(started_feature(feature, on), "a reason", "someone", on)


def never(*_: object) -> Never:
    """A read or a write of the record that the remove of a Feature never asks for."""
    raise AssertionError("a remove reads the rows, the Feature and its work items")


def story(number: int, parent: Parent = ONE) -> WorkItem:
    """The Story of that number in Backlog under that parent, with one Task."""
    criterion = make_scenario("a state", "an action", "another")
    item = make_work_item(make_story_id(number), f"title {number}", criterion, "", CREATED, parent)
    return append_task(item, make_task(make_task_id(number), "a task", "an output", "", CREATED))


def started(number: int) -> WorkItemState:
    """The Story of that number under the Feature, started."""
    return started_work_item(story(number), BEGUN)


def blocked(number: int) -> WorkItemState:
    """The Story of that number under the Feature, started and then blocked."""
    return blocked_work_item(started(number), "no key", "developer", BEGUN)


def completed(number: int) -> WorkItemState:
    """The Story of that number under the Feature, completed with its one Task."""
    task = make_task_id(number)
    done = completed_task(started_task(started(number), task, BEGUN), task, BEGUN, NO_COMMIT)
    return completed_work_item(done, BEGUN, NO_COMMIT)


@dataclass
class Saved:
    """What a remove saved: the Features and the work items, in the order saved."""

    features: list[FeatureState] = field(default_factory=list[FeatureState])
    items: list[WorkItemState] = field(default_factory=list[WorkItemState])


def store(
    items: Sequence[WorkItemState] = (),
    feature: FeatureState = FEATURE,
    saved: Saved | None = None,
) -> Store:
    """The store of a record holding those Stories and that Feature as F-0001."""
    kept = Saved() if saved is None else saved
    held = {item.id: item for item in items}

    def load_feature(feature_id: FeatureId) -> FeatureState:
        if feature_id != ONE:
            raise FeatureNotFoundError(feature_id)
        return feature

    return Store(
        find_work_item_rows=lambda kind: (
            [work_item_row(item) for item in items] if kind == STORY else []
        ),
        load_work_item=held.__getitem__,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=kept.items.append,
        load_queue=lambda: make_queue([]),
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
        features=FeatureStore(load_feature, kept.features.append, lambda: ["F-0001"]),
    )


def remove(items: Sequence[WorkItemState], feature: FeatureState = FEATURE) -> Saved:
    """What the remove of F-0001 for the reason saved in a record holding those Stories."""
    saved = Saved()
    remove_named("F-0001", REASON, store(items, feature, saved), lambda: ON)
    return saved


@pytest.mark.model
def test_a_feature_in_backlog_is_removed_with_its_reason_and_its_time_to_the_second() -> None:
    assert removed_feature(FEATURE, REASON, ON) == RemovedFeature(
        ONE,
        "a title",
        "why",
        ("a criterion", "another"),
        CREATED,
        ON.replace(microsecond=0),
        REASON,
    )


@pytest.mark.model
@pytest.mark.parametrize(
    ("feature", "refusal", "error"),
    [
        (COMPLETED, CompletedAlreadyError, r"^F-0001 is completed already$"),
        (GONE, RemovedAlreadyError, REMOVED_ALREADY),
    ],
    ids=["completed", "removed"],
)
def test_a_completed_or_removed_feature_is_not_removed(
    feature: FeatureState, refusal: type[Exception], error: str
) -> None:
    with pytest.raises(refusal, match=error):
        removed_feature(feature, "a reason", ON)


@pytest.mark.model
def test_a_remove_with_a_blank_reason_is_refused() -> None:
    with pytest.raises(EmptyPartError, match=r"^reason is empty$"):
        removed_feature(FEATURE, " ", ON)


@pytest.mark.model
@pytest.mark.parametrize(
    "begun", [started_feature, blocked_in_progress], ids=["started", "blocked"]
)
def test_a_feature_in_progress_with_a_line_and_a_term_is_removed_as_one_in_backlog_is(
    begun: Callable[[FeatureState, datetime], FeatureState],
) -> None:
    assert removed_feature(begun(NOTED, BEGUN), REASON, ON) == removed_feature(NOTED, REASON, ON)


@pytest.mark.model
def test_a_remove_of_a_started_feature_with_a_blank_reason_is_refused() -> None:
    with pytest.raises(EmptyPartError, match=r"^reason is empty$"):
        removed_feature(STARTED, " ", ON)


@pytest.mark.model
def test_a_removed_feature_is_not_started() -> None:
    with pytest.raises(RemovedAlreadyError, match=REMOVED_ALREADY):
        started_feature(GONE, ON)


@pytest.mark.model
def test_a_removed_feature_is_not_blocked() -> None:
    with pytest.raises(RemovedAlreadyError, match=REMOVED_ALREADY):
        blocked_feature(GONE, "a reason", "someone", ON)


@pytest.mark.model
def test_a_removed_feature_is_not_unblocked() -> None:
    with pytest.raises(NotBlockedError, match=r"^F-0001 is not blocked$"):
        unblocked_feature(GONE)


@pytest.mark.model
def test_a_removed_feature_is_not_completed() -> None:
    with pytest.raises(RemovedAlreadyError, match=REMOVED_ALREADY):
        completed_feature(GONE, ON, NO_COMMIT)


@pytest.mark.model
def test_a_removed_feature_is_not_amended() -> None:
    with pytest.raises(RemovedAlreadyError, match=REMOVED_ALREADY):
        amended_feature(GONE, FeatureAmendment(title="one more"))


@pytest.mark.view
def test_the_row_of_a_removed_feature_is_in_removed_by_its_own_state_with_its_reason() -> None:
    assert feature_row(GONE, ["removed"]) == FeatureRow(
        "F-0001", "a title", "Removed", completed=0, held=0, reason=REASON
    )


@pytest.mark.view
def test_the_detail_of_a_removed_feature_names_its_reason_and_waits_on_nothing() -> None:
    detail = feature_detail(GONE)
    assert (detail.reason, detail.waiting_on) == (REASON, "")


@pytest.mark.view
def test_a_removed_feature_is_listed_under_removed_with_its_reason_and_no_progress() -> None:
    row = FeatureRow("F-0001", "a title", "Removed", completed=0, held=0, reason=REASON)
    assert status_text([row]).splitlines()[-3:] == [
        "Removed (1)",
        "  F-0001  a title",
        "  filed by mistake",
    ]


@pytest.mark.view
def test_a_removed_feature_is_shown_removed_with_its_reason_and_its_work_items() -> None:
    held = [removed_work_item(story(1), REASON, ON)]
    assert show_feature_item("F-0001", store(held, GONE)) == (
        "F-0001  a title\n"
        "  bucket       Removed\n"
        "  reason       filed by mistake\n"
        "  description  why\n"
        "Criteria (2)\n"
        "  a criterion\n"
        "  another\n"
        "Work items (1)\n"
        "  S-0001  title 1  Removed\n"
    )


@pytest.mark.edge
def test_a_removed_feature_is_written_with_its_state_line_its_removed_time_and_its_reason(
    tmp_path: Path,
) -> None:
    write_feature(tmp_path, GONE)
    assert tomllib.loads((tmp_path / FILE).read_text("utf-8")) == {
        "id": "F-0001",
        "state": "removed",
        "title": "a title",
        "description": "why",
        "created": CREATED,
        "removed": ON.replace(microsecond=0),
        "reason": REASON,
        "criteria": ["a criterion", "another"],
    }


@pytest.mark.edge
def test_a_removed_feature_reads_back_whole(tmp_path: Path) -> None:
    write_feature(tmp_path, GONE)
    assert read_feature(tmp_path, ONE) == GONE


@pytest.mark.edge
@pytest.mark.parametrize(
    "lines",
    [
        'state = "removed"\nreason = "a reason"\n',
        'state = "removed"\nremoved = 2026-01-03 09:00:00+00:00\n',
        'removed = 2026-01-03 09:00:00+00:00\nreason = "a reason"\n',
    ],
    ids=["removed-without-its-time", "removed-without-its-reason", "in-backlog-with-a-removal"],
)
def test_a_file_whose_state_line_and_the_removal_it_holds_disagree_is_refused_naming_it(
    lines: str, tmp_path: Path
) -> None:
    (tmp_path / "items").mkdir()
    (tmp_path / FILE).write_text(f"{lines}{WRITTEN_BEFORE}", "utf-8")
    with pytest.raises(FeatureFileError, match=r"F-0001.toml holds no Feature: "):
        read_feature(tmp_path, ONE)


@pytest.mark.command
def test_a_feature_removed_says_its_id_and_the_message_of_its_commit() -> None:
    removed = remove_named("F-0001", REASON, store([story(1)]), lambda: ON)
    assert removed == Written("removed F-0001\n", "chore: remove F-0001 in the record")


@pytest.mark.command
def test_a_feature_removed_is_saved_before_its_work_items_removed_for_the_same_reason() -> None:
    saved = remove([story(1), story(2), story(3, STANDALONE)])
    assert (saved.features, saved.items) == (
        [GONE],
        [removed_work_item(story(1), REASON, ON), removed_work_item(story(2), REASON, ON)],
    )


@pytest.mark.command
def test_a_work_item_of_it_removed_before_stays_as_it_was() -> None:
    before = removed_work_item(story(1), "superseded", BEGUN)
    assert remove([before, story(2)]).items == [removed_work_item(story(2), REASON, ON)]


@pytest.mark.command
def test_a_feature_without_a_work_item_is_removed_alone() -> None:
    saved = remove([])
    assert (saved.features, saved.items) == ([GONE], [])


@pytest.mark.command
@pytest.mark.parametrize("feature", [STARTED, BLOCKED], ids=["started", "blocked"])
def test_a_feature_in_progress_keeps_its_completed_work_item_and_one_removed_before(
    feature: FeatureState,
) -> None:
    before = removed_work_item(story(2), "superseded", BEGUN)
    saved = remove([completed(1), before], feature)
    assert (saved.features, saved.items) == ([removed_feature(feature, REASON, ON)], [])


@pytest.mark.command
def test_a_started_feature_is_removed_with_its_work_item_in_backlog_beside_a_completed_one() -> (
    None
):
    saved = remove([completed(1), story(2)], STARTED)
    assert (saved.features, saved.items) == (
        [removed_feature(STARTED, REASON, ON)],
        [removed_work_item(story(2), REASON, ON)],
    )


@pytest.mark.command
def test_a_started_feature_without_a_work_item_is_removed_alone() -> None:
    saved = remove([], STARTED)
    assert (saved.features, saved.items) == ([removed_feature(STARTED, REASON, ON)], [])


@pytest.mark.command
@pytest.mark.parametrize("feature", [STARTED, BLOCKED], ids=["started", "blocked"])
def test_a_feature_in_progress_that_holds_a_started_work_item_is_refused_and_saves_nothing(
    feature: FeatureState,
) -> None:
    saved = Saved()
    with pytest.raises(StartedAlreadyError, match=r"^F-0001 cannot be removed: S-0002 is started"):
        remove_named("F-0001", REASON, store([story(1), started(2)], feature, saved), lambda: ON)
    assert (saved.features, saved.items) == ([], [])


@pytest.mark.command
@pytest.mark.parametrize(
    ("items", "refusal", "error"),
    [
        (
            [story(1), started(2)],
            StartedAlreadyError,
            r"^F-0001 cannot be removed: S-0002 is started already$",
        ),
        (
            [completed(1), story(2)],
            CompletedAlreadyError,
            r"^F-0001 cannot be removed: S-0001 is completed already$",
        ),
        (
            [story(1), blocked(2)],
            BlockedError,
            r"^F-0001 cannot be removed: S-0002 is blocked$",
        ),
    ],
    ids=["a-started-work-item", "a-completed-work-item", "a-blocked-work-item"],
)
def test_a_feature_never_started_that_holds_a_work_item_begun_is_not_removed(
    items: list[WorkItemState], refusal: type[Exception], error: str
) -> None:
    with pytest.raises(refusal, match=error):
        remove(items)


@pytest.mark.command
@pytest.mark.parametrize(
    ("items", "feature", "reason"),
    [
        ([story(1), started(2)], FEATURE, REASON),
        ([started(1)], STARTED, REASON),
        ([story(1)], FEATURE, " "),
    ],
    ids=["a-started-work-item", "a-started-feature", "a-blank-reason"],
)
def test_a_remove_refused_saves_nothing(
    items: list[WorkItemState], feature: FeatureState, reason: str
) -> None:
    saved = Saved()
    with pytest.raises(ValueError, match=r"started already|reason is empty"):
        remove_named("F-0001", reason, store(items, feature, saved), lambda: ON)
    assert (saved.features, saved.items) == ([], [])


@pytest.mark.command
def test_a_remove_on_the_branch_of_a_work_item_is_refused_and_saves_nothing() -> None:
    saved = Saved()
    scope = Scope("wi/S-0009-a-slug", make_story_id(9))
    scoped = within(store([story(1)], saved=saved), lambda: scope, never)
    with pytest.raises(OutOfScopeError, match=r"^F-0001 is not written here: "):
        remove_named("F-0001", REASON, scoped, lambda: ON)
    assert (saved.features, saved.items) == ([], [])


@pytest.mark.command
def test_a_feature_the_record_does_not_hold_is_not_removed() -> None:
    with pytest.raises(FeatureNotFoundError, match=r"^no Feature F-0009 in the record$"):
        remove_named("F-0009", REASON, store(), lambda: ON)


@pytest.mark.command
def test_any_other_id_is_removed_as_a_work_item() -> None:
    removed = remove_named("S-0001", REASON, store([story(1, STANDALONE)]), lambda: ON)
    assert removed == Written("removed S-0001\n", "chore: remove S-0001 in the record")


@pytest.mark.command
def test_a_task_of_a_started_story_is_removed_and_its_story_saved() -> None:
    saved = Saved()
    remove_named("T-0001", REASON, store([started(1)], saved=saved), lambda: ON)
    assert saved.items == [removed_task(started(1), make_task_id(1), REASON, ON)]


@pytest.mark.command
def test_a_task_removed_says_its_id_its_story_and_the_message_of_its_commit() -> None:
    removed = remove_named("T-0001", REASON, store([started(1)]), lambda: ON)
    assert removed == Written(
        "removed T-0001 of S-0001\n", "chore: remove T-0001 of S-0001 in the record"
    )


@pytest.mark.command
def test_a_task_given_what_supersedes_it_is_refused_and_saves_nothing() -> None:
    saved = Saved()
    with pytest.raises(
        RelationError, match=r"^T-0001 is a Task: it is removed with --reason alone$"
    ):
        remove_named("T-0001", REASON, store([started(1)], saved=saved), lambda: ON, "S-0002")
    assert (saved.features, saved.items) == ([], [])


@pytest.mark.command
def test_a_work_item_added_under_a_removed_feature_is_refused() -> None:
    with pytest.raises(RemovedAlreadyError, match=REMOVED_ALREADY):
        parent_named("F-0001", store(feature=GONE))


@pytest.mark.command
def test_a_work_item_put_under_a_removed_feature_is_refused() -> None:
    with pytest.raises(
        RemovedAlreadyError, match=r"^S-0002 cannot be put under F-0001: F-0001 is removed already$"
    ):
        check_move(lambda _: GONE, S2, STANDALONE, ONE)


@pytest.mark.command
def test_a_work_item_in_backlog_under_a_removed_feature_is_not_started() -> None:
    with pytest.raises(
        RemovedAlreadyError, match=r"^S-0001 cannot start: F-0001 is removed already$"
    ):
        check_start_under_feature("S-0001", store([story(1)], GONE))
