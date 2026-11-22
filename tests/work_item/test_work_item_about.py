"""The terms a work item is about: kept by its moves, rewritten by an amend, read back whole."""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.knowledge import FINDING, make_knowledge_line
from flowgraph.task import completed, make_task, make_task_id, started
from flowgraph.work_item import (
    Amendment,
    WorkItem,
    WorkItemState,
    amended_work_item,
    append_task,
    completed_work_item,
    make_kind,
    make_work_item,
    make_work_item_id,
    noted_work_item,
    read_work_item,
    read_work_item_detail,
    removed_work_item,
    started_work_item,
    write_work_item,
)

pytestmark = pytest.mark.edge

CHORE = make_kind("Chore", "a", "CH")
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
ID = make_work_item_id(CHORE, 1)
TASK = make_task(make_task_id(1), "a task title", "an output", "", CREATED)
ABOUT: WorkItem = make_work_item(
    ID, "a title", make_scenario("a", "b", "c"), "", CREATED, about=("gate", "lane")
)
TASKED = append_task(ABOUT, TASK)
STARTED = started_work_item(TASKED, ON)
DONE = completed(started(TASK, ON), ON, make_commit("abc1234"))
COMPLETED = completed_work_item(replace(STARTED, tasks=(DONE,)), ON, make_commit("abc1234"))


def test_a_work_item_is_made_about_no_term_by_default() -> None:
    bare = make_work_item(ID, "a title", make_scenario("a", "b", "c"), "", CREATED)
    assert bare.about == ()


def test_a_work_item_is_made_about_the_terms_given_in_order() -> None:
    assert ABOUT.about == ("gate", "lane")


def test_a_started_work_item_is_about_the_terms_it_was() -> None:
    assert STARTED.about == ("gate", "lane")


def test_a_completed_work_item_is_about_the_terms_it_was() -> None:
    assert COMPLETED.about == ("gate", "lane")


def test_a_removed_work_item_is_about_the_terms_it_was() -> None:
    assert removed_work_item(ABOUT, "a reason", ON).about == ("gate", "lane")


@pytest.mark.parametrize("item", [ABOUT, STARTED, COMPLETED], ids=["backlog", "started", "done"])
def test_the_terms_are_read_back_as_written(tmp_path: Path, item: WorkItemState) -> None:
    write_work_item(tmp_path, item)
    assert read_work_item(tmp_path, ID).about == ("gate", "lane")


def test_the_terms_are_read_back_by_the_detail_as_plain_data(tmp_path: Path) -> None:
    write_work_item(tmp_path, ABOUT)
    assert read_work_item_detail(tmp_path, ID).about == ["gate", "lane"]


def test_the_terms_of_a_line_are_read_back_as_written(tmp_path: Path) -> None:
    line = make_knowledge_line(FINDING, "a text", ON, ("lane",))
    write_work_item(tmp_path, noted_work_item(ABOUT, line))
    assert read_work_item(tmp_path, ID).knowledge[0].about == ("lane",)


def test_the_terms_of_a_line_are_read_back_by_the_detail_as_plain_data(tmp_path: Path) -> None:
    line = make_knowledge_line(FINDING, "a text", ON, ("lane",))
    write_work_item(tmp_path, noted_work_item(ABOUT, line))
    assert read_work_item_detail(tmp_path, ID).knowledge[0].about == ["lane"]


def test_an_amend_gives_the_terms_in_place_of_those_it_had() -> None:
    assert amended_work_item(ABOUT, Amendment(about=("lane",))).about == ("lane",)


def test_an_amend_given_no_term_takes_them_all_away() -> None:
    assert amended_work_item(ABOUT, Amendment(about=())).about == ()


def test_an_amend_of_another_part_leaves_the_terms() -> None:
    assert amended_work_item(ABOUT, Amendment(title="another")).about == ("gate", "lane")
