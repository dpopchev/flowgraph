"""The answer no of the closing of a completed work item: kept, with the Bug it files."""

import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import (
    NO_COMMIT,
    Criterion,
    Decision,
    Defect,
    Hypothesis,
    make_defect,
    make_hypothesis,
    make_scenario,
)
from flowgraph.parent import STANDALONE, Parent, make_feature_id
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    Kind,
    NotVerifiableError,
    Verification,
    VerifiedAlreadyError,
    WorkItemFileError,
    WorkItemId,
    WorkItemRow,
    WorkItemState,
    append_task,
    completed_task,
    completed_work_item,
    make_kind,
    make_work_item,
    make_work_item_id,
    read_work_item,
    started_task,
    started_work_item,
    verified_work_item,
    verify_work_item_no,
    work_item_row,
    write_work_item,
)

CHORE = make_kind("Chore", "a", "CH")
FAULT = make_kind("Fault", "a", "FA", Defect)
PROBE = make_kind("Probe", "a", "PR", Hypothesis)
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, microsecond=500, tzinfo=UTC)
TEXT = "status listed no reason"
TASK = make_task(make_task_id(1), "a task title", "an output", "", CREATED)


def completed(kind: Kind, criterion: Criterion, decision: Decision | None = None) -> WorkItemState:
    """A work item of that kind with one Task, started and completed."""
    made = make_work_item(make_work_item_id(kind, 1), "a title", criterion, "", CREATED)
    begun = started_task(started_work_item(append_task(made, TASK), ON), make_task_id(1), ON)
    done = completed_task(begun, make_task_id(1), ON, NO_COMMIT)
    return completed_work_item(done, ON, NO_COMMIT, decision)


CHORE_DONE = completed(CHORE, make_scenario("a", "b", "c"))
FAULT_DONE = completed(FAULT, make_defect("it fails", "it works"))
PROBE_DONE = completed(PROBE, make_hypothesis("a question"), Decision("yes", "yes"))
ANSWER_NO = Verification("no", TEXT, ON.replace(microsecond=0))


@pytest.mark.model
def test_a_completed_work_item_keeps_the_answer_no_with_the_text_and_the_time() -> None:
    assert verified_work_item(CHORE_DONE, TEXT, ON, "no").verified == ANSWER_NO


def verify_no(
    item: WorkItemState, rows: list[WorkItemRow] | None = None, join: Parent = STANDALONE
) -> tuple[WorkItemId, list[WorkItemState]]:
    """Answer no on the work item, its Bugs of the kind Fault; the Bug id and what was saved."""
    saved: list[WorkItemState] = []
    added = verify_work_item_no(
        item_id=item.id,
        text=TEXT,
        bug=FAULT,
        find_bug_rows=lambda: [] if rows is None else rows,
        join=lambda _: join,
        load_work_item=lambda _: item,
        save_work_item=saved.append,
        now=lambda: ON,
    )
    return added, saved


@pytest.mark.command
def test_a_no_saves_a_bug_in_backlog_amending_the_work_item_its_expected_the_then() -> None:
    _, saved = verify_no(CHORE_DONE)
    bug = make_work_item(
        make_work_item_id(FAULT, 1),
        "No at the verify of CH-0001: a title",
        make_defect(TEXT, "c"),
        "",
        ON,
        amends=make_work_item_id(CHORE, 1),
    )
    assert saved[0] == bug


@pytest.mark.command
def test_the_bug_takes_the_next_bug_id() -> None:
    added, _ = verify_no(CHORE_DONE, [work_item_row(FAULT_DONE)])
    assert added == make_work_item_id(FAULT, 2)


@pytest.mark.command
def test_the_bug_filed_on_a_bug_expects_what_that_bug_expected() -> None:
    _, saved = verify_no(FAULT_DONE, [work_item_row(FAULT_DONE)])
    assert saved[0].criterion == make_defect(TEXT, "it works")


@pytest.mark.command
def test_the_work_item_is_saved_after_the_bug_with_the_answer_no() -> None:
    _, saved = verify_no(CHORE_DONE)
    assert saved[1:] == [verified_work_item(CHORE_DONE, TEXT, ON, "no")]


@pytest.mark.command
def test_the_bug_is_added_under_the_parent_the_join_gives() -> None:
    _, saved = verify_no(CHORE_DONE, join=make_feature_id(1))
    assert saved[0].parent == make_feature_id(1)


@pytest.mark.command
def test_a_no_on_a_spike_is_refused_and_nothing_is_saved() -> None:
    saved: list[WorkItemState] = []
    with pytest.raises(NotVerifiableError):
        verify_work_item_no(
            item_id=PROBE_DONE.id,
            text=TEXT,
            bug=FAULT,
            find_bug_rows=list,
            join=lambda parent: parent,
            load_work_item=lambda _: PROBE_DONE,
            save_work_item=saved.append,
            now=lambda: ON,
        )
    assert saved == []


@pytest.mark.model
def test_a_no_after_a_yes_is_refused() -> None:
    first = verified_work_item(CHORE_DONE, "make check: all checks passed", ON)
    with pytest.raises(VerifiedAlreadyError, match=r"^CH-0001 is verified already$"):
        verified_work_item(first, TEXT, ON, "no")


@pytest.mark.edge
def test_the_answer_no_is_read_back_whole(tmp_path: Path) -> None:
    verified = verified_work_item(CHORE_DONE, TEXT, ON, "no")
    write_work_item(tmp_path, verified)
    assert read_work_item(tmp_path, make_work_item_id(CHORE, 1)) == verified


@pytest.mark.edge
def test_a_file_with_another_answer_is_refused_naming_the_file(tmp_path: Path) -> None:
    write_work_item(tmp_path, verified_work_item(CHORE_DONE, TEXT, ON, "no"))
    path = tmp_path / "items" / "CH-0001.toml"
    path.write_text(path.read_text("utf-8").replace('answer = "no"', 'answer = "maybe"'), "utf-8")
    with pytest.raises(WorkItemFileError, match=rf"^{re.escape(str(path))} holds no Chore: "):
        read_work_item(tmp_path, make_work_item_id(CHORE, 1))
