"""The agent of a work item: a word the start names, kept by the started and the completed one.

Read back whole from its file, refused when it is no agent, listed by the views of the item.
"""

import re
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.status import show_text
from flowgraph.task import completed, make_task, make_task_id, started
from flowgraph.work_item import (
    WorkItem,
    WorkItemFileError,
    WorkItemState,
    append_task,
    completed_work_item,
    make_kind,
    make_work_item,
    make_work_item_id,
    read_work_item,
    read_work_item_detail,
    started_work_item,
    work_item_detail,
    work_item_path,
    write_work_item,
)
from flowgraph.work_item.agent import (
    Agent,
    AgentError,
    agent_written,
    check_agent_taken,
    make_agent,
)
from flowgraph.work_item.handed import agent_text, handed_work_item

CHORE = make_kind("Chore", "a", "CH")
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
ID = make_work_item_id(CHORE, 1)
SCENARIO = make_scenario("a", "b", "c")
TASK = make_task(make_task_id(1), "a task title", "an output", "", CREATED)
BACKLOG: WorkItem = append_task(make_work_item(ID, "a title", SCENARIO, "", CREATED), TASK)
AGENT = Agent("sonnet-a1")
UNHANDED = started_work_item(BACKLOG, ON)
HANDED = handed_work_item(UNHANDED, AGENT)
DONE = completed(started(TASK, ON), ON, make_commit("abc1234"))
COMPLETED = completed_work_item(replace(HANDED, tasks=(DONE,)), ON, make_commit("abc1234"))
CONFIG = Path("/src/project/.fgraph/config.toml")


@pytest.mark.model
@pytest.mark.parametrize(
    "word", ["a", "sonnet-a1", "a.b_c:d/e-f", "A" * 32], ids=["one", "model", "marks", "longest"]
)
def test_a_word_of_letters_digits_and_the_marks_is_an_agent(word: str) -> None:
    assert make_agent(word) == Agent(word)


@pytest.mark.model
@pytest.mark.parametrize(
    "word", ["", "two words", "a" * 33, "a,b", "agent\n", "agént"], ids=lambda w: repr(w)[:12]
)
def test_any_other_word_is_refused_naming_what_an_agent_is(word: str) -> None:
    said = f"{word!r} is no agent: it is one word of at most 32 letters, digits and . _ : / -"
    with pytest.raises(AgentError, match=f"^{re.escape(said)}$"):
        make_agent(word)


@pytest.mark.model
def test_an_empty_text_is_no_agent_as_written() -> None:
    assert agent_written("") is None


@pytest.mark.model
def test_a_text_is_the_agent_it_names_as_written() -> None:
    assert agent_written("sonnet-a1") == AGENT


@pytest.mark.model
def test_a_started_work_item_has_no_agent_until_one_is_handed() -> None:
    assert UNHANDED.agent is None


@pytest.mark.model
def test_a_started_work_item_handed_to_an_agent_holds_it() -> None:
    assert HANDED.agent == AGENT


@pytest.mark.model
def test_handing_a_work_item_to_none_leaves_it_as_it_was() -> None:
    assert handed_work_item(UNHANDED, None) == UNHANDED


@pytest.mark.model
def test_a_completed_work_item_keeps_the_agent_it_had() -> None:
    assert COMPLETED.agent == AGENT


@pytest.mark.model
def test_a_completed_work_item_of_one_without_an_agent_has_none() -> None:
    done = completed_work_item(replace(UNHANDED, tasks=(DONE,)), ON, make_commit("abc1234"))
    assert done.agent is None


@pytest.mark.model
def test_the_text_of_the_agent_of_a_started_work_item_is_its_name() -> None:
    assert agent_text(HANDED) == "sonnet-a1"


@pytest.mark.model
def test_the_text_of_the_agent_of_a_completed_work_item_is_its_name() -> None:
    assert agent_text(COMPLETED) == "sonnet-a1"


@pytest.mark.model
def test_the_text_of_the_agent_of_a_work_item_without_one_is_empty() -> None:
    assert agent_text(UNHANDED) == ""


@pytest.mark.model
def test_the_text_of_the_agent_of_a_work_item_in_backlog_is_empty() -> None:
    assert agent_text(BACKLOG) == ""


@pytest.mark.model
def test_a_start_that_names_an_agent_with_the_development_on_is_taken() -> None:
    assert check_agent_taken("S-0001", "sonnet-a1", True, CONFIG) is None


@pytest.mark.model
@pytest.mark.parametrize("development_on", [True, False])
def test_a_start_that_names_no_agent_is_taken(development_on: bool) -> None:
    assert check_agent_taken("S-0001", None, development_on, CONFIG) is None


@pytest.mark.model
def test_an_agent_given_with_the_development_off_is_refused_naming_the_key() -> None:
    with pytest.raises(
        AgentError,
        match=(
            r"^S-0001 takes no --agent: the development is off, so no agent is handed work"
            r" -- set development\.enabled = true in /src/project/\.fgraph/config\.toml$"
        ),
    ):
        check_agent_taken("S-0001", "sonnet-a1", False, CONFIG)


@pytest.mark.model
def test_a_name_that_is_no_agent_is_refused_with_the_development_on() -> None:
    with pytest.raises(AgentError, match=r"^'two words' is no agent: "):
        check_agent_taken("S-0001", "two words", True, CONFIG)


@pytest.mark.edge
@pytest.mark.parametrize("item", [HANDED, COMPLETED], ids=["started", "completed"])
def test_the_agent_is_read_back_as_written(tmp_path: Path, item: WorkItemState) -> None:
    write_work_item(tmp_path, item)
    assert agent_text(read_work_item(tmp_path, ID)) == "sonnet-a1"


@pytest.mark.edge
def test_a_file_holds_the_key_agent_only_when_it_has_one(tmp_path: Path) -> None:
    write_work_item(tmp_path, UNHANDED)
    assert "agent" not in work_item_path(tmp_path, ID).read_text(encoding="utf-8")


@pytest.mark.edge
def test_a_file_without_the_key_is_read_as_none(tmp_path: Path) -> None:
    write_work_item(tmp_path, UNHANDED)
    assert agent_text(read_work_item(tmp_path, ID)) == ""


@pytest.mark.edge
def test_a_file_holding_a_name_that_is_no_agent_is_refused_naming_the_file(tmp_path: Path) -> None:
    write_work_item(tmp_path, HANDED)
    path = work_item_path(tmp_path, ID)
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace('agent = "sonnet-a1"', 'agent = "a b"'), encoding="utf-8")
    with pytest.raises(WorkItemFileError, match=r"CH-0001\.toml holds no Chore: 'a b' is no agent"):
        read_work_item(tmp_path, ID)


@pytest.mark.edge
def test_the_detail_read_from_the_file_holds_the_agent_as_the_word(tmp_path: Path) -> None:
    write_work_item(tmp_path, HANDED)
    assert read_work_item_detail(tmp_path, ID).agent == "sonnet-a1"


@pytest.mark.view
def test_the_detail_of_a_work_item_holds_its_agent_as_the_word() -> None:
    assert work_item_detail(HANDED).agent == "sonnet-a1"


@pytest.mark.view
def test_the_detail_of_a_work_item_without_one_holds_it_empty() -> None:
    assert work_item_detail(UNHANDED).agent == ""


@pytest.mark.view
def test_show_lists_the_agent_before_the_commit() -> None:
    lines = show_text(work_item_detail(COMPLETED)).splitlines()
    assert lines[lines.index("  agent        sonnet-a1") + 1].startswith("  commit")


@pytest.mark.view
def test_show_lists_no_agent_line_for_a_work_item_without_one() -> None:
    assert "agent" not in show_text(work_item_detail(UNHANDED))
