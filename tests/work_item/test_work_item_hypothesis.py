"""A hypothesis and its answer: a work item that states one is completed with its decision."""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import (
    Answer,
    DecisionError,
    EmptyPartError,
    Hypothesis,
    make_commit,
    make_hypothesis,
    make_scenario,
)
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    Amendment,
    NoSuchPartError,
    WorkItemFileError,
    WorkItemState,
    amended_work_item,
    append_task,
    completed_task,
    completed_work_item,
    make_kind,
    make_work_item,
    make_work_item_id,
    read_work_item,
    read_work_item_detail,
    started_task,
    started_work_item,
    work_item_detail,
    write_work_item,
)

CHORE = make_kind("Chore", "a", "CH")
PROBE = make_kind("Probe", "a", "PR", Hypothesis)
ONE = make_work_item_id(PROBE, 1)
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
COMMIT = make_commit("abc1234")
QUESTION = make_hypothesis("Can one file hold the record?")
TASK = make_task(make_task_id(3), "a task title", "an output", "", CREATED)
ITEM = append_task(make_work_item(ONE, "a title", QUESTION, "", CREATED), TASK)
READY = completed_task(
    started_task(started_work_item(ITEM, ON), make_task_id(3), ON), make_task_id(3), ON, COMMIT
)
SETTLED = completed_work_item(READY, ON, COMMIT, "yes, one file")
PLAIN = append_task(
    make_work_item(
        make_work_item_id(CHORE, 1), "a title", make_scenario("a", "b", "c"), "", CREATED
    ),
    TASK,
)
PLAIN_READY = completed_task(
    started_task(started_work_item(PLAIN, ON), make_task_id(3), ON), make_task_id(3), ON, COMMIT
)
FILE = Path("items") / "PR-0001.toml"


@pytest.mark.model
def test_a_hypothesis_states_its_question() -> None:
    assert make_hypothesis("Can it?") == Hypothesis("Can it?")


@pytest.mark.model
def test_a_blank_hypothesis_is_refused() -> None:
    with pytest.raises(EmptyPartError, match=r"^hypothesis is empty$"):
        make_hypothesis(" ")


@pytest.mark.model
def test_a_work_item_that_states_a_hypothesis_is_completed_with_its_decision() -> None:
    assert SETTLED.criterion == Answer("Can one file hold the record?", "yes, one file")


@pytest.mark.model
def test_a_hypothesis_is_not_completed_without_its_decision() -> None:
    with pytest.raises(
        DecisionError, match=r"^PR-0001 is completed with its decision: it states a hypothesis$"
    ):
        completed_work_item(READY, ON, COMMIT)


@pytest.mark.model
def test_a_blank_decision_is_refused() -> None:
    with pytest.raises(EmptyPartError, match=r"^decision is empty$"):
        completed_work_item(READY, ON, COMMIT, " ")


@pytest.mark.model
def test_a_work_item_with_another_criterion_takes_no_decision() -> None:
    with pytest.raises(
        DecisionError,
        match=r"^CH-0001 takes no decision: only a Spike is completed with one$",
    ):
        completed_work_item(PLAIN_READY, ON, COMMIT, "yes")


@pytest.mark.model
def test_a_hypothesis_is_amended() -> None:
    amended = amended_work_item(ITEM, Amendment(hypothesis="Can two files hold it?"))
    assert amended.criterion == Hypothesis("Can two files hold it?")


@pytest.mark.model
def test_a_part_of_a_given_when_then_is_refused_on_a_hypothesis() -> None:
    with pytest.raises(
        NoSuchPartError, match=r"^PR-0001 has no given, when or then: it states a hypothesis$"
    ):
        amended_work_item(ITEM, Amendment(then="another state"))


@pytest.mark.model
def test_a_hypothesis_is_refused_on_a_given_when_then() -> None:
    with pytest.raises(
        NoSuchPartError,
        match=r"^CH-0001 has no hypothesis: it states a Given / When / Then$",
    ):
        amended_work_item(PLAIN, Amendment(hypothesis="Can it?"))


@pytest.mark.view
def test_the_detail_of_a_settled_work_item_names_its_hypothesis_and_its_decision() -> None:
    detail = work_item_detail(SETTLED)
    assert (detail.hypothesis, detail.decision) == (
        "Can one file hold the record?",
        "yes, one file",
    )


@pytest.mark.model
def test_a_work_item_is_completed_with_the_decision_given() -> None:
    assert completed_work_item(READY, ON, COMMIT, "yes, one file") == SETTLED


@pytest.mark.edge
def test_a_hypothesis_is_written_as_the_criterion_table_of_the_file(tmp_path: Path) -> None:
    write_work_item(tmp_path, ITEM)
    assert tomllib.loads((tmp_path / FILE).read_text("utf-8"))["criterion"] == {
        "hypothesis": "Can one file hold the record?"
    }


@pytest.mark.edge
def test_the_decision_is_written_beside_the_hypothesis_it_answers(tmp_path: Path) -> None:
    write_work_item(tmp_path, SETTLED)
    assert tomllib.loads((tmp_path / FILE).read_text("utf-8"))["criterion"] == {
        "hypothesis": "Can one file hold the record?",
        "decision": "yes, one file",
    }


@pytest.mark.edge
@pytest.mark.parametrize("item", [ITEM, READY, SETTLED], ids=["backlog", "started", "settled"])
def test_a_work_item_with_a_hypothesis_reads_back_whole(
    tmp_path: Path, item: WorkItemState
) -> None:
    write_work_item(tmp_path, item)
    assert read_work_item(tmp_path, ONE) == item


@pytest.mark.edge
def test_the_detail_read_from_the_file_names_the_hypothesis_and_the_decision(
    tmp_path: Path,
) -> None:
    write_work_item(tmp_path, SETTLED)
    assert read_work_item_detail(tmp_path, ONE) == work_item_detail(SETTLED)


@pytest.mark.edge
def test_a_file_holding_a_decision_before_it_is_completed_is_refused(tmp_path: Path) -> None:
    write_work_item(tmp_path, make_work_item(ONE, "a title", QUESTION, "", CREATED))
    path = tmp_path / FILE
    path.write_text(path.read_text("utf-8") + 'decision = "yes"\n', "utf-8")
    with pytest.raises(
        WorkItemFileError,
        match=r"PR-0001.toml holds no Probe: a Probe holds its decision once it is completed$",
    ):
        read_work_item(tmp_path, ONE)
