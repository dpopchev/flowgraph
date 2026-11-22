"""The answer of a hypothesis: yes or no, taken at the completion beside its decision."""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import (
    Answer,
    Decision,
    DecisionError,
    Hypothesis,
    make_commit,
    make_decision,
    make_hypothesis,
)
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    WorkItemFileError,
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
NO = completed_work_item(READY, ON, COMMIT, Decision("too big", "no"))
FILE = Path("items") / "PR-0001.toml"


@pytest.mark.model
def test_a_hypothesis_completed_with_the_answer_no_holds_it_beside_its_decision() -> None:
    assert NO.criterion == Answer("Can one file hold the record?", "too big", "no")


@pytest.mark.model
def test_a_hypothesis_completed_with_a_decision_and_no_answer_is_refused_naming_it() -> None:
    with pytest.raises(DecisionError, match=r"^PR-0001 is completed with its answer: yes or no$"):
        completed_work_item(READY, ON, COMMIT, Decision("too big", None))


@pytest.mark.model
def test_a_decision_is_made_with_its_answer() -> None:
    assert make_decision("too big", "no") == Decision("too big", "no")


@pytest.mark.model
def test_a_decision_is_made_with_none_when_neither_is_given() -> None:
    assert make_decision(None, None) is None


@pytest.mark.model
def test_an_answer_given_without_its_decision_is_refused() -> None:
    with pytest.raises(DecisionError, match=r"^an answer is given beside its decision$"):
        make_decision(None, "no")


@pytest.mark.view
def test_the_detail_of_an_answered_work_item_names_the_answer() -> None:
    assert work_item_detail(NO).answer == "no"


@pytest.mark.edge
def test_the_answer_is_written_beside_the_decision(tmp_path: Path) -> None:
    write_work_item(tmp_path, NO)
    assert tomllib.loads((tmp_path / FILE).read_text("utf-8"))["criterion"] == {
        "hypothesis": "Can one file hold the record?",
        "decision": "too big",
        "answer": "no",
    }


@pytest.mark.edge
def test_a_work_item_with_an_answer_reads_back_whole(tmp_path: Path) -> None:
    write_work_item(tmp_path, NO)
    assert read_work_item(tmp_path, ONE) == NO


@pytest.mark.edge
def test_the_detail_read_from_the_file_names_the_answer(tmp_path: Path) -> None:
    write_work_item(tmp_path, NO)
    assert read_work_item_detail(tmp_path, ONE).answer == "no"


@pytest.mark.edge
def test_a_file_holding_a_decision_and_no_answer_is_read_as_before(tmp_path: Path) -> None:
    write_work_item(tmp_path, NO)
    path = tmp_path / FILE
    path.write_text(path.read_text("utf-8").replace('answer = "no"\n', ""), "utf-8")
    assert read_work_item(tmp_path, ONE).criterion == Answer(
        "Can one file hold the record?", "too big"
    )


@pytest.mark.edge
def test_a_file_holding_an_answer_other_than_yes_or_no_is_refused_naming_the_file(
    tmp_path: Path,
) -> None:
    write_work_item(tmp_path, NO)
    path = tmp_path / FILE
    path.write_text(path.read_text("utf-8").replace('answer = "no"', 'answer = "maybe"'), "utf-8")
    with pytest.raises(WorkItemFileError, match=r"PR-0001.toml"):
        read_work_item(tmp_path, ONE)
