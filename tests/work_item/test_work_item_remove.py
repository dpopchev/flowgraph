"""The remove of a work item: one in Backlog is removed with its reason, and kept in its file."""

import tomllib
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
import tomli_w

from flowgraph.criterion import EmptyPartError, make_commit, make_scenario
from flowgraph.knowledge import FINDING, make_knowledge_line
from flowgraph.parent import make_feature_id
from flowgraph.relation import RelationError, make_relations
from flowgraph.task import (
    CompletedAlreadyError,
    RemovedTask,
    TaskRow,
    blocked,
    completed,
    make_task,
    make_task_id,
    removed,
    started,
)
from flowgraph.work_item import (
    Amendment,
    BlockedWorkItem,
    RemovedAlreadyError,
    RemovedWorkItem,
    StartedWorkItem,
    WorkItemFileError,
    WorkItemRow,
    amended_work_item,
    append_task,
    blocked_work_item,
    commit_sha,
    completed_task,
    completed_work_item,
    make_kind,
    make_work_item,
    make_work_item_id,
    read_work_item,
    read_work_item_detail,
    read_work_item_rows,
    removed_work_item,
    started_task,
    started_work_item,
    state_name,
    still_open,
    work_item_detail,
    work_item_row,
    write_work_item,
)

CHORE = make_kind("Chore", "a", "CH")
ONE = make_work_item_id(CHORE, 1)
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, 500, tzinfo=UTC)
COMMIT = make_commit("abc1234")
SCENARIO = make_scenario("a state", "an action", "another state")
TASK = make_task(make_task_id(3), "a task title", "an output", "", CREATED)
ITEM = append_task(make_work_item(ONE, "a title", SCENARIO, "why", CREATED), TASK)
BEGUN = started_work_item(ITEM, ON)
GONE = removed_work_item(ITEM, "filed by mistake", ON)
FILE = Path("items") / "CH-0001.toml"


@pytest.mark.model
def test_a_work_item_in_backlog_is_removed_with_its_reason_and_keeps_its_tasks() -> None:
    assert removed_work_item(ITEM, "filed by mistake", ON) == RemovedWorkItem(
        ONE,
        "a title",
        SCENARIO,
        "why",
        CREATED,
        ON.replace(microsecond=0),
        "filed by mistake",
        (TASK,),
    )


LATE = datetime(2026, 1, 3, 10, 0, 0, 500, tzinfo=UTC)
FIVE = [make_task(make_task_id(n), f"task {n}", "an output", "", CREATED) for n in range(1, 6)]
DONE = completed(started(FIVE[0], ON), ON, COMMIT)
GOING = started(FIVE[1], ON)
STUCK = blocked(started(FIVE[2], ON), "no key", "developer", ON)
DROPPED = removed(FIVE[4], "not needed", ON)
WORKED = replace(BEGUN, tasks=(DONE, GOING, STUCK, FIVE[3], DROPPED))
HELD = blocked_work_item(WORKED, "no key", "developer", ON)
PIVOTED = (
    DONE,
    removed(GOING, "pivoted", LATE),
    removed(STUCK, "pivoted", LATE),
    removed(FIVE[3], "pivoted", LATE),
    DROPPED,
)
FEATURE = make_feature_id(1)
RICH = replace(
    WORKED,
    parent=FEATURE,
    complexity="high",
    knowledge=(make_knowledge_line(FINDING, "a text", ON),),
    relations=make_relations(ONE, depends_on=[make_work_item_id(CHORE, 3)]),
    about=("a term",),
)


@pytest.mark.model
@pytest.mark.parametrize("item", [WORKED, HELD], ids=["started", "blocked"])
def test_a_started_work_item_keeps_its_done_tasks_and_removes_the_others(
    item: StartedWorkItem | BlockedWorkItem,
) -> None:
    assert removed_work_item(item, "pivoted", LATE) == RemovedWorkItem(
        ONE,
        "a title",
        SCENARIO,
        "why",
        CREATED,
        LATE.replace(microsecond=0),
        "pivoted",
        PIVOTED,
    )


@pytest.mark.model
def test_a_started_work_item_removed_keeps_its_knowledge_relations_parent_and_about() -> None:
    gone = removed_work_item(RICH, "pivoted", LATE)
    assert (gone.knowledge, gone.relations, gone.parent, gone.complexity, gone.about) == (
        RICH.knowledge,
        RICH.relations,
        FEATURE,
        "high",
        ("a term",),
    )


@pytest.mark.model
def test_the_tasks_of_a_started_item_superseded_with_no_reason_name_what_supersedes_it() -> None:
    gone = removed_work_item(WORKED, " ", LATE, make_work_item_id(CHORE, 2))
    assert [task.reason for task in gone.tasks[1:4] if isinstance(task, RemovedTask)] == [
        "superseded by CH-0002"
    ] * 3


@pytest.mark.model
def test_a_started_work_item_removed_with_a_blank_reason_is_refused() -> None:
    with pytest.raises(EmptyPartError, match=r"^reason is empty$"):
        removed_work_item(WORKED, " ", LATE)


@pytest.mark.edge
def test_a_started_work_item_removed_reads_back_whole(tmp_path: Path) -> None:
    gone = removed_work_item(WORKED, "pivoted", LATE)
    write_work_item(tmp_path, gone)
    assert read_work_item(tmp_path, ONE) == gone


@pytest.mark.edge
def test_a_started_work_item_removed_is_written_with_its_task_tables_in_order(
    tmp_path: Path,
) -> None:
    write_work_item(tmp_path, removed_work_item(WORKED, "pivoted", LATE))
    written = tomllib.loads((tmp_path / FILE).read_text("utf-8"))
    assert [(task["id"], task["state"]) for task in written["tasks"]] == [
        ("T-0001", "completed"),
        ("T-0002", "removed"),
        ("T-0003", "removed"),
        ("T-0004", "removed"),
        ("T-0005", "removed"),
    ]


@pytest.mark.edge
def test_a_removed_file_that_holds_a_started_task_is_refused_naming_it(tmp_path: Path) -> None:
    write_work_item(tmp_path, removed_work_item(WORKED, "pivoted", LATE))
    held = tomllib.loads((tmp_path / FILE).read_text("utf-8"))
    table = {**held["tasks"][1], "state": "started", "started": ON}
    held["tasks"][1] = {key: table[key] for key in table if key not in ("removed", "reason")}
    (tmp_path / FILE).write_text(tomli_w.dumps(held), encoding="utf-8")
    with pytest.raises(WorkItemFileError, match=r"CH-0001\.toml holds no Chore"):
        read_work_item(tmp_path, ONE)


@pytest.mark.view
def test_the_row_of_a_started_work_item_removed_holds_its_task_states() -> None:
    row = work_item_row(removed_work_item(WORKED, "pivoted", LATE))
    assert (row.state, [task.state for task in row.tasks]) == (
        "removed",
        ["completed", "removed", "removed", "removed", "removed"],
    )


@pytest.mark.model
def test_a_completed_work_item_is_not_removed() -> None:
    done = completed_task(started_task(BEGUN, make_task_id(3), ON), make_task_id(3), ON, COMMIT)
    with pytest.raises(CompletedAlreadyError, match=r"^CH-0001 is completed already$"):
        removed_work_item(completed_work_item(done, ON, COMMIT), "a reason", ON)


@pytest.mark.model
def test_a_removed_work_item_is_not_removed_once_more() -> None:
    with pytest.raises(RemovedAlreadyError, match=r"^CH-0001 is removed already$"):
        removed_work_item(GONE, "a reason", ON)


@pytest.mark.model
def test_a_remove_with_a_blank_reason_is_refused() -> None:
    with pytest.raises(EmptyPartError, match=r"^reason is empty$"):
        removed_work_item(ITEM, " ", ON)


@pytest.mark.model
def test_a_removed_work_item_takes_no_task() -> None:
    with pytest.raises(RemovedAlreadyError, match=r"^CH-0001 is removed already$"):
        still_open(GONE)


@pytest.mark.model
def test_a_removed_work_item_is_not_started() -> None:
    with pytest.raises(RemovedAlreadyError, match=r"^CH-0001 is removed already$"):
        started_work_item(GONE, ON)


@pytest.mark.model
def test_a_removed_work_item_is_not_amended() -> None:
    with pytest.raises(RemovedAlreadyError, match=r"^CH-0001 is removed already$"):
        amended_work_item(GONE, Amendment(title="one more"))


@pytest.mark.model
def test_a_removed_work_item_is_not_completed() -> None:
    with pytest.raises(RemovedAlreadyError, match=r"^CH-0001 is removed already$"):
        completed_work_item(GONE, ON, COMMIT)


@pytest.mark.model
def test_a_removed_work_item_is_named_removed_and_has_no_commit() -> None:
    assert (state_name(GONE), commit_sha(GONE)) == ("removed", "")


@pytest.mark.view
def test_the_row_of_a_removed_work_item_names_its_reason() -> None:
    tasks = [TaskRow("T-0003", "a task title", "an output", "", "backlog")]
    assert work_item_row(GONE) == WorkItemRow(
        "CH-0001", "a title", "removed", reason="filed by mistake", created=CREATED, tasks=tasks
    )


@pytest.mark.view
def test_the_detail_of_a_removed_work_item_names_its_reason() -> None:
    assert work_item_detail(GONE).reason == "filed by mistake"


@pytest.mark.edge
def test_a_removed_work_item_is_written_with_its_removal(tmp_path: Path) -> None:
    write_work_item(tmp_path, GONE)
    written = tomllib.loads((tmp_path / FILE).read_text("utf-8"))
    assert (written["state"], written["removed"], written["reason"]) == (
        "removed",
        ON.replace(microsecond=0),
        "filed by mistake",
    )


@pytest.mark.edge
def test_a_removed_work_item_reads_back_whole(tmp_path: Path) -> None:
    write_work_item(tmp_path, GONE)
    assert read_work_item(tmp_path, ONE) == GONE


@pytest.mark.edge
def test_the_row_read_from_the_file_of_a_removed_work_item_names_its_reason(
    tmp_path: Path,
) -> None:
    write_work_item(tmp_path, GONE)
    assert read_work_item_rows(tmp_path, CHORE) == [work_item_row(GONE)]


OTHER = make_work_item_id(CHORE, 2)
SUPERSEDED = removed_work_item(ITEM, "refiled", ON, OTHER)


@pytest.mark.model
def test_a_removed_work_item_keeps_the_work_item_that_supersedes_it() -> None:
    assert SUPERSEDED.superseded_by == OTHER


@pytest.mark.model
def test_a_removed_work_item_with_a_reason_alone_is_superseded_by_none() -> None:
    assert GONE.superseded_by is None


@pytest.mark.model
def test_a_removed_work_item_superseded_by_another_needs_no_reason() -> None:
    assert removed_work_item(ITEM, "", ON, OTHER).reason == ""


@pytest.mark.model
def test_a_work_item_superseded_by_itself_is_refused() -> None:
    with pytest.raises(RelationError, match=r"^CH-0001 cannot be superseded by itself$"):
        removed_work_item(ITEM, "a reason", ON, ONE)


@pytest.mark.view
def test_the_row_of_a_removed_work_item_names_what_supersedes_it() -> None:
    assert work_item_row(SUPERSEDED).superseded_by == "CH-0002"


@pytest.mark.view
def test_the_detail_of_a_removed_work_item_names_what_supersedes_it() -> None:
    assert work_item_detail(SUPERSEDED).superseded_by == "CH-0002"


@pytest.mark.edge
def test_a_superseded_work_item_is_written_with_what_supersedes_it(tmp_path: Path) -> None:
    write_work_item(tmp_path, SUPERSEDED, [CHORE])
    written = tomllib.loads((tmp_path / FILE).read_text("utf-8"))
    assert written["superseded_by"] == "CH-0002"


@pytest.mark.edge
def test_a_superseded_work_item_reads_back_whole(tmp_path: Path) -> None:
    write_work_item(tmp_path, SUPERSEDED, [CHORE])
    assert read_work_item(tmp_path, ONE, [CHORE]) == SUPERSEDED


@pytest.mark.edge
def test_the_row_read_from_the_file_of_a_superseded_work_item_names_what_supersedes_it(
    tmp_path: Path,
) -> None:
    write_work_item(tmp_path, SUPERSEDED, [CHORE])
    assert read_work_item_rows(tmp_path, CHORE)[0].superseded_by == "CH-0002"


@pytest.mark.edge
def test_the_detail_read_from_the_file_of_a_superseded_work_item_names_it(tmp_path: Path) -> None:
    write_work_item(tmp_path, SUPERSEDED, [CHORE])
    assert read_work_item_detail(tmp_path, ONE).superseded_by == "CH-0002"
