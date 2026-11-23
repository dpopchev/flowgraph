"""The start of a work item driven by an agent: what the check lets pass and what it refuses.

The development driven by an agent asks a work item of a complexity beside its Task. A work item
with no Task, one past Backlog, a Task, a Feature and a text that is no id are left to the start.
"""

from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.development.driver import NoComplexityError, asks_complexity, check_complexity
from flowgraph.record import Config, make_config
from flowgraph.story import make_story_id
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    LoadWorkItem,
    WorkItem,
    WorkItemState,
    append_task,
    make_complexity,
    make_work_item,
    started_work_item,
)

pytestmark = pytest.mark.command

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
AGENT = make_config('[development]\nenabled = true\ndriver = "agent"\n')
DEVELOPER = make_config('[development]\nenabled = true\ndriver = "developer"\n')
OFF = make_config('[development]\ndriver = "agent"\n')


def story(*, tasks: int = 1, complexity: str | None = None) -> WorkItem:
    """S-0002 in Backlog, with that many Tasks and that complexity, none by default."""
    held = None if complexity is None else make_complexity(complexity)
    item = make_work_item(
        make_story_id(2),
        "a title",
        make_scenario("a state", "an action", "another"),
        "",
        CREATED,
        complexity=held,
    )
    for _ in range(tasks):
        item = append_task(item, make_task(make_task_id(1), "a task", "an output", "", CREATED))
    return item


def never(*_: object) -> Never:
    """The load of the work item, for a start the check passes without a read."""
    raise AssertionError("the check reads a work item of a development driven by an agent alone")


def loading(held: WorkItemState) -> LoadWorkItem:
    """A load that gives that work item whatever the id."""
    return lambda _: held


def test_a_story_in_backlog_with_a_task_and_no_complexity_is_refused_in_the_whole_line() -> None:
    with pytest.raises(NoComplexityError) as error:
        check_complexity("S-0002", loading(story()), AGENT)
    assert str(error.value) == (
        "S-0002 has no complexity to start with: "
        "set it with fgraph amend S-0002 --complexity low, medium or high"
    )


def test_a_story_with_a_task_and_a_complexity_passes() -> None:
    assert check_complexity("S-0002", loading(story(complexity="low")), AGENT) is None


def test_a_story_with_no_task_and_no_complexity_passes_to_the_start_that_refuses_it() -> None:
    assert check_complexity("S-0002", loading(story(tasks=0)), AGENT) is None


def test_a_story_started_passes_to_the_start_that_refuses_it() -> None:
    begun = started_work_item(story(), CREATED)
    assert check_complexity("S-0002", loading(begun), AGENT) is None


@pytest.mark.parametrize("item", ["T-0001", "F-0001", "no-id"], ids=["task", "feature", "no-id"])
def test_a_task_a_feature_and_a_text_that_is_no_id_pass_without_a_read(item: str) -> None:
    assert check_complexity(item, never, AGENT) is None


@pytest.mark.parametrize("config", [DEVELOPER, OFF], ids=["developer", "development-off"])
def test_a_start_not_driven_by_an_agent_passes_without_a_read(config: Config) -> None:
    assert check_complexity("S-0002", never, config) is None


def test_the_development_driven_by_an_agent_asks_a_complexity() -> None:
    assert asks_complexity(AGENT) is True


def test_the_development_driven_by_a_developer_asks_none() -> None:
    assert asks_complexity(DEVELOPER) is False


def test_the_development_off_asks_none_whoever_drives_it() -> None:
    assert asks_complexity(OFF) is False
