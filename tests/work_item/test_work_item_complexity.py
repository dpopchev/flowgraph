"""The complexity of a work item: kept by its moves, read back whole, refused when it is no word."""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.task import completed, make_task, make_task_id, started
from flowgraph.work_item import (
    COMPLEXITIES,
    ComplexityError,
    WorkItem,
    WorkItemFileError,
    WorkItemState,
    append_task,
    completed_work_item,
    make_complexity,
    make_kind,
    make_work_item,
    make_work_item_id,
    read_work_item,
    removed_work_item,
    started_work_item,
    work_item_path,
    write_work_item,
)

CHORE = make_kind("Chore", "a", "CH")
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
ID = make_work_item_id(CHORE, 1)
SCENARIO = make_scenario("a", "b", "c")
TASK = make_task(make_task_id(1), "a task title", "an output", "", CREATED)
HIGH: WorkItem = make_work_item(ID, "a title", SCENARIO, "", CREATED, complexity="high")
TASKED = append_task(HIGH, TASK)
STARTED = started_work_item(TASKED, ON)
DONE = completed(started(TASK, ON), ON, make_commit("abc1234"))
COMPLETED = completed_work_item(replace(STARTED, tasks=(DONE,)), ON, make_commit("abc1234"))


@pytest.mark.model
def test_a_work_item_is_made_with_no_complexity_by_default() -> None:
    assert make_work_item(ID, "a title", SCENARIO, "", CREATED).complexity is None


@pytest.mark.model
def test_a_work_item_is_made_with_the_complexity_given() -> None:
    assert HIGH.complexity == "high"


@pytest.mark.model
def test_a_started_work_item_has_the_complexity_it_had() -> None:
    assert STARTED.complexity == "high"


@pytest.mark.model
def test_a_completed_work_item_has_the_complexity_it_had() -> None:
    assert COMPLETED.complexity == "high"


@pytest.mark.model
def test_a_removed_work_item_has_the_complexity_it_had() -> None:
    assert removed_work_item(HIGH, "a reason", ON).complexity == "high"


@pytest.mark.model
@pytest.mark.parametrize("word", ["low", "medium", "high"])
def test_a_word_of_the_three_is_a_complexity(word: str) -> None:
    assert make_complexity(word) == word


@pytest.mark.model
def test_the_three_complexities_are_listed_in_order() -> None:
    assert COMPLEXITIES == ("low", "medium", "high")


@pytest.mark.model
@pytest.mark.parametrize("word", ["huge", "High", ""])
def test_any_other_word_is_refused_naming_the_three(word: str) -> None:
    with pytest.raises(
        ComplexityError, match=rf"^--complexity {word!r} is none of low, medium, high$"
    ):
        make_complexity(word)


@pytest.mark.edge
@pytest.mark.parametrize("item", [HIGH, STARTED, COMPLETED], ids=["backlog", "started", "done"])
def test_the_complexity_is_read_back_as_written(tmp_path: Path, item: WorkItemState) -> None:
    write_work_item(tmp_path, item)
    assert read_work_item(tmp_path, ID).complexity == "high"


@pytest.mark.edge
def test_the_complexity_of_a_removed_work_item_is_read_back_as_written(tmp_path: Path) -> None:
    write_work_item(tmp_path, removed_work_item(HIGH, "a reason", ON))
    assert read_work_item(tmp_path, ID).complexity == "high"


@pytest.mark.edge
def test_a_file_holds_the_key_complexity_only_when_it_has_one(tmp_path: Path) -> None:
    write_work_item(tmp_path, make_work_item(ID, "a title", SCENARIO, "", CREATED))
    assert "complexity" not in work_item_path(tmp_path, ID).read_text(encoding="utf-8")


@pytest.mark.edge
def test_a_file_without_the_key_is_read_as_none(tmp_path: Path) -> None:
    write_work_item(tmp_path, make_work_item(ID, "a title", SCENARIO, "", CREATED))
    assert read_work_item(tmp_path, ID).complexity is None


@pytest.mark.edge
def test_a_file_holding_another_word_is_refused_naming_it(tmp_path: Path) -> None:
    write_work_item(tmp_path, HIGH)
    path = work_item_path(tmp_path, ID)
    path.write_text(path.read_text(encoding="utf-8").replace("high", "huge"), encoding="utf-8")
    with pytest.raises(WorkItemFileError, match=r"CH-0001\.toml holds no Chore"):
        read_work_item(tmp_path, ID)
