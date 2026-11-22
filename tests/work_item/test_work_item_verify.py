"""The answer of the closing of a completed work item: kept, refused, written and read back."""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import (
    NO_COMMIT,
    Criterion,
    Defect,
    EmptyPartError,
    Hypothesis,
    make_defect,
    make_hypothesis,
    make_scenario,
)
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    Kind,
    NotVerifiableError,
    Verification,
    VerifiedAlreadyError,
    VerifiedRow,
    WorkItemState,
    append_task,
    completed_task,
    completed_work_item,
    make_kind,
    make_verification,
    make_work_item,
    make_work_item_id,
    read_work_item,
    read_work_item_detail,
    removed_work_item,
    started_task,
    started_work_item,
    verified_work_item,
    verify_work_item,
    write_work_item,
)

CHORE = make_kind("Chore", "a", "CH")
FAULT = make_kind("Fault", "a", "FA", Defect)
PROBE = make_kind("Probe", "a", "PR", Hypothesis)
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, microsecond=500, tzinfo=UTC)
TEXT = "make check: all checks passed"
TASK = make_task(make_task_id(1), "a task title", "an output", "", CREATED)


def completed(kind: Kind, criterion: Criterion, decision: str | None = None) -> WorkItemState:
    """A work item of that kind with one Task, started and completed."""
    made = make_work_item(make_work_item_id(kind, 1), "a title", criterion, "", CREATED)
    item = append_task(made, TASK)
    begun = started_task(started_work_item(item, ON), make_task_id(1), ON)
    done = completed_task(begun, make_task_id(1), ON, NO_COMMIT)
    return completed_work_item(done, ON, NO_COMMIT, decision)


CHORE_DONE = completed(CHORE, make_scenario("a", "b", "c"))
FAULT_DONE = completed(FAULT, make_defect("it fails", "it works"))
PROBE_DONE = completed(PROBE, make_hypothesis("a question"), "yes")
ANSWER = Verification("yes", TEXT, ON.replace(microsecond=0))


@pytest.mark.model
@pytest.mark.parametrize("item", [CHORE_DONE, FAULT_DONE], ids=["scenario", "defect"])
def test_a_completed_work_item_keeps_the_answer_yes_with_the_text_and_the_time(
    item: WorkItemState,
) -> None:
    assert verified_work_item(item, TEXT, ON).verified == ANSWER


@pytest.mark.model
def test_the_time_of_the_answer_is_kept_to_the_second() -> None:
    assert make_verification("yes", TEXT, ON).on == ON.replace(microsecond=0)


@pytest.mark.model
def test_a_blank_text_is_refused() -> None:
    with pytest.raises(EmptyPartError, match=r"^text is empty$"):
        make_verification("yes", " ", ON)


@pytest.mark.model
@pytest.mark.parametrize(
    ("item", "words"),
    [
        (
            make_work_item(
                make_work_item_id(CHORE, 1), "a title", make_scenario("a", "b", "c"), "", CREATED
            ),
            "CH-0001 is backlog: fgraph verify takes a completed Story, Bug or Upkeep",
        ),
        (
            started_work_item(
                append_task(
                    make_work_item(
                        make_work_item_id(CHORE, 1), "a", make_scenario("a", "b", "c"), "", CREATED
                    ),
                    TASK,
                ),
                ON,
            ),
            "CH-0001 is started: fgraph verify takes a completed Story, Bug or Upkeep",
        ),
        (
            removed_work_item(
                make_work_item(
                    make_work_item_id(CHORE, 1), "a", make_scenario("a", "b", "c"), "", CREATED
                ),
                "a reason",
                ON,
            ),
            "CH-0001 is removed: fgraph verify takes a completed Story, Bug or Upkeep",
        ),
        (PROBE_DONE, "PR-0001 is a Spike: fgraph verify takes a completed Story, Bug or Upkeep"),
    ],
    ids=["backlog", "started", "removed", "a-spike"],
)
def test_a_work_item_that_is_not_a_completed_story_bug_or_upkeep_is_refused(
    item: WorkItemState, words: str
) -> None:
    with pytest.raises(NotVerifiableError) as refused:
        verified_work_item(item, TEXT, ON)
    assert str(refused.value) == words


@pytest.mark.model
def test_a_second_answer_is_refused_and_the_first_stays() -> None:
    first = verified_work_item(CHORE_DONE, TEXT, ON)
    with pytest.raises(VerifiedAlreadyError, match=r"^CH-0001 is verified already$"):
        verified_work_item(first, "another text", ON)


@pytest.mark.command
def test_the_command_saves_the_work_item_whole_with_its_answer() -> None:
    saved: list[WorkItemState] = []
    verify_work_item(
        item_id=make_work_item_id(CHORE, 1),
        text=TEXT,
        load_work_item=lambda _: CHORE_DONE,
        save_work_item=saved.append,
        now=lambda: ON,
    )
    assert saved == [verified_work_item(CHORE_DONE, TEXT, ON)]


@pytest.mark.command
def test_the_command_saves_nothing_for_a_work_item_not_completed() -> None:
    saved: list[WorkItemState] = []
    backlog = make_work_item(
        make_work_item_id(CHORE, 1), "a title", make_scenario("a", "b", "c"), "", CREATED
    )
    with pytest.raises(NotVerifiableError):
        verify_work_item(
            item_id=make_work_item_id(CHORE, 1),
            text=TEXT,
            load_work_item=lambda _: backlog,
            save_work_item=saved.append,
            now=lambda: ON,
        )
    assert saved == []


@pytest.mark.edge
def test_the_answer_is_written_as_a_table_of_the_file(tmp_path: Path) -> None:
    write_work_item(tmp_path, verified_work_item(CHORE_DONE, TEXT, ON))
    written = tomllib.loads((tmp_path / "items" / "CH-0001.toml").read_text("utf-8"))
    assert written["verified"] == {"answer": "yes", "text": TEXT, "on": ANSWER.on}


@pytest.mark.edge
def test_the_answer_is_read_back_whole(tmp_path: Path) -> None:
    verified = verified_work_item(CHORE_DONE, TEXT, ON)
    write_work_item(tmp_path, verified)
    assert read_work_item(tmp_path, make_work_item_id(CHORE, 1)) == verified


@pytest.mark.edge
def test_a_file_without_an_answer_is_read_as_before(tmp_path: Path) -> None:
    write_work_item(tmp_path, CHORE_DONE)
    assert read_work_item(tmp_path, make_work_item_id(CHORE, 1)) == CHORE_DONE


@pytest.mark.edge
def test_a_file_without_an_answer_holds_no_table_for_it(tmp_path: Path) -> None:
    write_work_item(tmp_path, CHORE_DONE)
    written = tomllib.loads((tmp_path / "items" / "CH-0001.toml").read_text("utf-8"))
    assert "verified" not in written


@pytest.mark.edge
def test_the_detail_read_from_the_file_lists_the_answer(tmp_path: Path) -> None:
    write_work_item(tmp_path, verified_work_item(CHORE_DONE, TEXT, ON))
    detail = read_work_item_detail(tmp_path, make_work_item_id(CHORE, 1))
    assert detail.verified == VerifiedRow("yes", TEXT, ANSWER.on)
