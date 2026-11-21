"""The amend of a work item of any kind: in Backlog, each part named is rewritten, the rest kept."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from flowgraph.criterion import EmptyPartError, make_commit, make_scenario
from flowgraph.task import (
    CompletedAlreadyError,
    StartedAlreadyError,
    make_task,
    make_task_id,
)
from flowgraph.work_item import (
    Amendment,
    NoPartError,
    WorkItem,
    amended_work_item,
    append_task,
    completed_task,
    completed_work_item,
    make_kind,
    make_work_item,
    make_work_item_id,
    started_task,
    started_work_item,
)

pytestmark = pytest.mark.model

CHORE = make_kind("Chore", "a", "CH")
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
COMMIT = make_commit("abc1234")
SCENARIO = make_scenario("a state", "an action", "another state")
BARE = make_work_item(make_work_item_id(CHORE, 1), "a title", SCENARIO, "why", CREATED)
ITEM = append_task(BARE, make_task(make_task_id(1), "a task title", "an output", "how", CREATED))
BEGUN = started_work_item(ITEM, ON)
FINISHED = completed_task(started_task(BEGUN, make_task_id(1), ON), make_task_id(1), ON, COMMIT)
WHOLE = completed_work_item(FINISHED, ON, COMMIT)


@pytest.mark.parametrize(
    ("amendment", "amended"),
    [
        (Amendment(title="another title"), replace(ITEM, title="another title")),
        (Amendment(description="why not"), replace(ITEM, description="why not")),
        (
            Amendment(given="a new state"),
            replace(ITEM, criterion=make_scenario("a new state", "an action", "another state")),
        ),
        (
            Amendment(when="a new action"),
            replace(ITEM, criterion=make_scenario("a state", "a new action", "another state")),
        ),
        (
            Amendment(then="a new state"),
            replace(ITEM, criterion=make_scenario("a state", "an action", "a new state")),
        ),
    ],
    ids=["title", "description", "given", "when", "then"],
)
def test_a_part_named_is_rewritten_and_the_rest_is_as_it_was(
    amendment: Amendment, amended: WorkItem
) -> None:
    assert amended_work_item(ITEM, amendment) == amended


def test_several_parts_named_are_rewritten_together() -> None:
    amendment = Amendment(title="another title", when="a new action", description="why not")
    assert amended_work_item(ITEM, amendment) == replace(
        ITEM,
        title="another title",
        description="why not",
        criterion=make_scenario("a state", "a new action", "another state"),
    )


def test_a_blank_description_clears_it() -> None:
    assert amended_work_item(ITEM, Amendment(description="")).description == ""


@pytest.mark.parametrize(
    ("amendment", "part"),
    [
        (Amendment(title=" "), "title"),
        (Amendment(given=""), "given"),
        (Amendment(when="\t"), "when"),
        (Amendment(then=" "), "then"),
    ],
    ids=["title", "given", "when", "then"],
)
def test_a_blank_title_or_part_of_the_criterion_is_refused(amendment: Amendment, part: str) -> None:
    with pytest.raises(EmptyPartError, match=rf"^{part} is empty$"):
        amended_work_item(ITEM, amendment)


def test_an_amendment_naming_no_part_is_refused() -> None:
    with pytest.raises(NoPartError, match=r"^amend rewrites no part of CH-0001: name one$"):
        amended_work_item(ITEM, Amendment())


def test_a_started_work_item_is_not_amended() -> None:
    with pytest.raises(StartedAlreadyError, match=r"^CH-0001 is started already$"):
        amended_work_item(BEGUN, Amendment(then="a new state"))


def test_a_completed_work_item_is_not_amended() -> None:
    with pytest.raises(CompletedAlreadyError, match=r"^CH-0001 is completed already$"):
        amended_work_item(WHOLE, Amendment(then="a new state"))
