"""The amend of a started or blocked work item: its deviation is kept with the part rewritten.

A blocked one counts as started. The deviation is asked for once the item is started and refused
for one in Backlog; the complexity, the parent and what it depends on stay of the Backlog alone.
"""

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import pytest

from flowgraph.criterion import EmptyPartError, make_commit, make_scenario
from flowgraph.knowledge import DEVIATION, FINDING, KnowledgeLine, make_knowledge_line
from flowgraph.parent import STANDALONE
from flowgraph.task import (
    CompletedAlreadyError,
    StartedAlreadyError,
    make_task,
    make_task_id,
)
from flowgraph.work_item import (
    Amendment,
    DeviationError,
    NoPartError,
    NoSuchPartError,
    RemovedAlreadyError,
    WorkItemState,
    amend_work_item,
    amended_work_item,
    append_task,
    blocked_work_item,
    completed_task,
    completed_work_item,
    make_kind,
    make_work_item,
    make_work_item_id,
    noted_work_item,
    removed_work_item,
    started_task,
    started_work_item,
)

CHORE = make_kind("Chore", "a", "CH")
ID = make_work_item_id(CHORE, 1)
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
COMMIT = make_commit("abc1234")
FIRST = make_task_id(1)
SCENARIO = make_scenario("a state", "an action", "another state")
BARE = make_work_item(ID, "a title", SCENARIO, "why", CREATED)
IN_BACKLOG = append_task(BARE, make_task(FIRST, "a task title", "an output", "how", CREATED))
BEGUN = started_task(started_work_item(IN_BACKLOG, ON), FIRST, ON)
STUCK = blocked_work_item(BEGUN, "a reason", "the sponsor", ON)
WHOLE = completed_work_item(completed_task(BEGUN, FIRST, ON, COMMIT), ON, COMMIT)
GONE = removed_work_item(IN_BACKLOG, "filed by mistake", ON)
LINE = make_knowledge_line(DEVIATION, "the then is narrowed to one kind", ON)
KEPT = make_knowledge_line(FINDING, "a finding made before", ON)
NEEDED = (
    "^CH-0001 is started: amend it with --deviation TEXT, what changes in what it was agreed to do$"
)
BACKLOG_ALONE = (
    "^CH-0001 is started: its complexity, its parent and what it depends on are amended in "
    "Backlog alone$"
)
BOTH = pytest.mark.parametrize("item", [BEGUN, STUCK], ids=["started", "blocked"])
LINES = pytest.mark.parametrize("line", [LINE, None], ids=["with-a-line", "without-a-line"])


@pytest.mark.model
@BOTH
@pytest.mark.parametrize(
    ("amendment", "part"),
    [
        (Amendment(title="another title"), {"title": "another title"}),
        (Amendment(description="why not"), {"description": "why not"}),
        (
            Amendment(given="a new state"),
            {"criterion": make_scenario("a new state", "an action", "another state")},
        ),
        (Amendment(about=("a term",)), {"about": ("a term",)}),
    ],
    ids=["title", "description", "given", "about"],
)
def test_a_part_of_a_started_work_item_is_rewritten_with_its_deviation(
    item: WorkItemState, amendment: Amendment, part: dict[str, Any]
) -> None:
    assert amended_work_item(item, amendment, LINE) == replace(item, **part, knowledge=(LINE,))


@pytest.mark.model
@BOTH
def test_a_line_the_item_kept_stays_before_the_deviation(item: WorkItemState) -> None:
    kept = noted_work_item(item, KEPT)
    assert amended_work_item(kept, Amendment(title="another title"), LINE).knowledge == (KEPT, LINE)


@pytest.mark.model
@BOTH
def test_an_amend_without_a_deviation_of_a_started_work_item_is_refused(
    item: WorkItemState,
) -> None:
    with pytest.raises(DeviationError, match=NEEDED):
        amended_work_item(item, Amendment(title="another title"))


@pytest.mark.model
@BOTH
@LINES
@pytest.mark.parametrize(
    "amendment",
    [Amendment(complexity="high"), Amendment(parent=STANDALONE), Amendment(depends_on=())],
    ids=["complexity", "parent", "depends-on"],
)
def test_the_complexity_the_parent_and_the_terms_are_of_the_backlog_alone(
    item: WorkItemState, amendment: Amendment, line: KnowledgeLine | None
) -> None:
    with pytest.raises(StartedAlreadyError, match=BACKLOG_ALONE):
        amended_work_item(item, amendment, line)


@pytest.mark.model
@BOTH
@pytest.mark.parametrize("part", [Amendment(output="x"), Amendment(check="make test")])
def test_a_part_of_a_task_is_refused_for_a_started_work_item(
    item: WorkItemState, part: Amendment
) -> None:
    with pytest.raises(NoSuchPartError, match=r"^CH-0001 has no (output|check): only a Task"):
        amended_work_item(item, part, LINE)


@pytest.mark.model
@BOTH
def test_a_deviation_alone_amends_no_part_of_a_started_work_item(item: WorkItemState) -> None:
    with pytest.raises(NoPartError, match=r"^amend rewrites no part of CH-0001: name one$"):
        amended_work_item(item, Amendment(), LINE)


@pytest.mark.model
@BOTH
def test_a_blank_title_of_a_started_work_item_is_refused(item: WorkItemState) -> None:
    with pytest.raises(EmptyPartError, match=r"^title is empty$"):
        amended_work_item(item, Amendment(title=" "), LINE)


@pytest.mark.model
def test_a_deviation_for_a_work_item_in_backlog_is_refused() -> None:
    refusal = (
        "^CH-0001 is in Backlog: it has no agreed plan to deviate from -- "
        "amend it without --deviation$"
    )
    with pytest.raises(DeviationError, match=refusal):
        amended_work_item(IN_BACKLOG, Amendment(title="another title"), LINE)


@pytest.mark.model
def test_a_work_item_in_backlog_is_amended_without_a_deviation_as_before() -> None:
    amended = amended_work_item(IN_BACKLOG, Amendment(title="another title"))
    assert amended == replace(IN_BACKLOG, title="another title")


@pytest.mark.model
def test_a_completed_work_item_is_refused_with_a_deviation() -> None:
    with pytest.raises(CompletedAlreadyError, match=r"^CH-0001 is completed already$"):
        amended_work_item(WHOLE, Amendment(title="another title"), LINE)


@pytest.mark.model
def test_a_removed_work_item_is_refused_with_a_deviation() -> None:
    with pytest.raises(RemovedAlreadyError, match=r"^CH-0001 is removed already$"):
        amended_work_item(GONE, Amendment(title="another title"), LINE)


def never(*_: object) -> None:
    """A check of a move or of a criterion that an amend of a title never asks for."""
    raise AssertionError("an amend of a title checks no move and no criterion")


@pytest.mark.command
@BOTH
def test_amend_work_item_saves_the_started_work_item_once_holding_its_deviation(
    item: WorkItemState,
) -> None:
    saved: list[WorkItemState] = []
    amend_work_item(
        item_id=ID,
        amendment=Amendment(title="another title"),
        deviation=LINE,
        load_work_item=lambda _: item,
        save_work_item=saved.append,
        check_move=never,
        check_realizes=never,
    )
    assert saved == [replace(item, title="another title", knowledge=(LINE,))]


@pytest.mark.command
def test_amend_work_item_refused_for_want_of_a_deviation_saves_nothing() -> None:
    saved: list[WorkItemState] = []
    with pytest.raises(DeviationError):
        amend_work_item(
            item_id=ID,
            amendment=Amendment(title="another title"),
            load_work_item=lambda _: BEGUN,
            save_work_item=saved.append,
            check_move=never,
            check_realizes=never,
        )
    assert saved == []
