"""The evidence of a completed work item: its commit or none, kept in its file and its views."""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import (
    NO_COMMIT,
    Answer,
    CommitError,
    Evidence,
    Hypothesis,
    evidence_text,
    evidence_written,
    make_commit,
    make_hypothesis,
    make_scenario,
)
from flowgraph.status import show_text, status_text
from flowgraph.task import TaskRow, completed, make_task, make_task_id, started
from flowgraph.work_item import (
    WorkItemState,
    append_task,
    commit_sha,
    complete_task,
    completed_task,
    completed_work_item,
    make_kind,
    make_work_item,
    make_work_item_id,
    read_work_item,
    read_work_item_detail,
    read_work_item_rows,
    started_task,
    started_work_item,
    work_item_detail,
    work_item_row,
    write_work_item,
)

CHORE = make_kind("Chore", "a", "CH")
PROBE = make_kind("Probe", "a", "PR", Hypothesis)
ONE = make_work_item_id(CHORE, 1)
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
COMMIT = make_commit("abc1234")
SCENARIO = make_scenario("a state", "an action", "another state")
TASK = make_task(make_task_id(3), "a task title", "an output", "", CREATED)
ITEM = append_task(make_work_item(ONE, "a title", SCENARIO, "", CREATED), TASK)
HALF = started_task(started_work_item(ITEM, ON), make_task_id(3), ON)
READY = completed_task(HALF, make_task_id(3), ON, NO_COMMIT)
WHOLE = completed_work_item(READY, ON, NO_COMMIT)
MIXED = completed_work_item(completed_task(HALF, make_task_id(3), ON, COMMIT), ON, NO_COMMIT)
QUESTION = make_hypothesis("Can one file hold the record?")
ASKED = append_task(
    make_work_item(make_work_item_id(PROBE, 1), "a title", QUESTION, "", CREATED), TASK
)
SETTLED = completed_work_item(
    completed_task(
        started_task(started_work_item(ASKED, ON), make_task_id(3), ON),
        make_task_id(3),
        ON,
        NO_COMMIT,
    ),
    ON,
    NO_COMMIT,
    "yes, one file",
)
FILE = Path("items") / "CH-0001.toml"


def written(record: Path) -> dict[str, object]:
    """The file of CH-0001 in the record, as its primitives."""
    return tomllib.loads((record / FILE).read_text("utf-8"))


@pytest.mark.model
@pytest.mark.parametrize(
    ("text", "evidence"), [("", NO_COMMIT), ("abc1234", COMMIT)], ids=["none", "a-commit"]
)
def test_the_evidence_written_is_the_commit_of_the_sha_or_none(
    text: str, evidence: Evidence
) -> None:
    assert evidence_written(text) == evidence


@pytest.mark.model
@pytest.mark.parametrize(
    ("evidence", "text"), [(NO_COMMIT, ""), (COMMIT, "abc1234")], ids=["none", "a-commit"]
)
def test_the_evidence_is_written_as_its_sha_or_nothing(evidence: Evidence, text: str) -> None:
    assert evidence_text(evidence) == text


@pytest.mark.model
def test_an_evidence_written_as_no_sha_is_refused() -> None:
    with pytest.raises(CommitError, match=r"^'xyz' is no commit: it is 7 to 40 hex digits$"):
        evidence_written("xyz")


@pytest.mark.model
def test_a_task_completed_without_a_commit_in_its_work_item_holds_none() -> None:
    assert READY.tasks == (completed(started(TASK, ON), ON, NO_COMMIT),)


@pytest.mark.model
def test_a_work_item_completed_without_a_commit_holds_none() -> None:
    assert WHOLE.commit == NO_COMMIT


@pytest.mark.model
def test_a_work_item_completed_without_a_commit_names_no_sha() -> None:
    assert commit_sha(WHOLE) == ""


@pytest.mark.model
def test_a_hypothesis_completed_without_a_commit_holds_its_decision_beside_none() -> None:
    assert (SETTLED.criterion, SETTLED.commit) == (
        Answer("Can one file hold the record?", "yes, one file"),
        NO_COMMIT,
    )


@pytest.mark.view
def test_the_row_and_the_detail_of_a_work_item_completed_without_a_commit_carry_none() -> None:
    assert (work_item_row(WHOLE).commit, work_item_detail(WHOLE).commit) == ("", "")


@pytest.mark.view
def test_the_row_of_a_task_completed_without_a_commit_carries_none() -> None:
    assert work_item_row(WHOLE).tasks == [
        TaskRow("T-0003", "a task title", "an output", "", "completed")
    ]


@pytest.mark.view
def test_status_lists_a_work_item_completed_without_a_commit_by_id_and_title_alone() -> None:
    assert status_text([work_item_row(WHOLE)]) == (
        "Backlog (0)\nInProgress (0)\nCompleted (1)\n  CH-0001  a title\n"
    )


@pytest.mark.view
def test_show_lists_no_commit_line_of_a_work_item_completed_without_one() -> None:
    assert show_text(work_item_detail(WHOLE)) == (
        "CH-0001  a title\n"
        "  bucket       Completed\n"
        "  given        a state\n"
        "  when         an action\n"
        "  then         another state\n"
        "Tasks (1)\n"
        "  T-0003  a task title\n"
        "    bucket           Completed\n"
        "    expected output  an output\n"
    )


@pytest.mark.command
def test_a_task_is_completed_without_a_commit_in_the_work_item_that_holds_it() -> None:
    saved: list[WorkItemState] = []
    complete_task(
        task_id=make_task_id(3),
        commit=NO_COMMIT,
        load_holder=lambda _: HALF,
        save_work_item=saved.append,
        now=lambda: ON,
    )
    assert saved == [READY]


@pytest.mark.model
def test_a_work_item_is_completed_without_a_commit() -> None:
    assert completed_work_item(READY, ON, NO_COMMIT) == WHOLE


@pytest.mark.edge
def test_a_work_item_completed_without_a_commit_is_written_without_a_commit(
    tmp_path: Path,
) -> None:
    write_work_item(tmp_path, MIXED)
    assert "commit" not in written(tmp_path)


@pytest.mark.edge
def test_a_task_completed_without_a_commit_is_written_without_a_commit(tmp_path: Path) -> None:
    write_work_item(tmp_path, READY)
    assert written(tmp_path)["tasks"] == [
        {
            "id": "T-0003",
            "state": "completed",
            "title": "a task title",
            "expected_output": "an output",
            "created": CREATED,
            "started": ON,
            "completed": ON,
        }
    ]


@pytest.mark.edge
@pytest.mark.parametrize(
    "item",
    [READY, WHOLE, MIXED, SETTLED],
    ids=["task-without-a-commit", "without-a-commit", "task-in-a-commit", "settled"],
)
def test_a_work_item_reads_back_with_the_evidence_of_each(
    tmp_path: Path, item: WorkItemState
) -> None:
    write_work_item(tmp_path, item)
    assert read_work_item(tmp_path, item.id) == item


@pytest.mark.edge
def test_the_row_and_the_detail_read_from_the_file_carry_no_commit(tmp_path: Path) -> None:
    write_work_item(tmp_path, WHOLE)
    assert (read_work_item_rows(tmp_path, CHORE), read_work_item_detail(tmp_path, ONE)) == (
        [work_item_row(WHOLE)],
        work_item_detail(WHOLE),
    )
