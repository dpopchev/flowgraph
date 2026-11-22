"""The verify command of a work item: it loads the completed item, answers its closing, saves it.

A no moves nothing backwards: the work item stays completed and the no adds, in the same write,
a Bug in Backlog that amends it, built as `fgraph add bug` builds one.
"""

from collections.abc import Callable
from typing import assert_never

from flowgraph.criterion import Answer, Defect, Hypothesis, Scenario, make_defect
from flowgraph.parent import Parent
from flowgraph.record import Now
from flowgraph.work_item.commands import add_work_item
from flowgraph.work_item.id import Kind, WorkItemId, work_item_id_text
from flowgraph.work_item.model import (
    CompletedWorkItem,
    FindWorkItemRows,
    LoadWorkItem,
    SaveWorkItem,
)
from flowgraph.work_item.moves import verified_work_item
from flowgraph.work_item.verification import TAKES, NotVerifiableError

# The parent the Bug a no files is added under, from the parent of the work item it amends.
JoinParent = Callable[[Parent], Parent]


def verify_work_item(
    *,
    item_id: WorkItemId,
    text: str,
    load_work_item: LoadWorkItem,
    save_work_item: SaveWorkItem,
    now: Now,
) -> None:
    """Keep the answer yes of the closing of the work item of that id, with the text the run of
    its criterion printed and the time now, and save it whole.

    Raises WorkItemNotFoundError when the record holds no such item, NotVerifiableError when it
    is not completed or is a Spike, VerifiedAlreadyError when it holds an answer already and
    EmptyPartError when the text is blank; nothing is saved.
    """
    save_work_item(verified_work_item(load_work_item(item_id), text, now()))


def _expected_of(item: CompletedWorkItem) -> str:
    """What the Bug a no files expects: the Then of a Story or an Upkeep, the expected of a Bug.

    Raises NotVerifiableError for a Spike, which takes no answer of a closing.
    """
    match item.criterion:
        case Scenario():
            return item.criterion.then
        case Defect():
            return item.criterion.expected
        case Hypothesis() | Answer():
            raise NotVerifiableError(f"{work_item_id_text(item.id)} is a Spike: {TAKES}")
        case _ as unreachable:
            assert_never(unreachable)


def verify_work_item_no(
    *,
    item_id: WorkItemId,
    text: str,
    bug: Kind,
    find_bug_rows: FindWorkItemRows,
    join: JoinParent,
    load_work_item: LoadWorkItem,
    save_work_item: SaveWorkItem,
    now: Now,
) -> WorkItemId:
    """Keep the answer no of the closing of the work item of that id and add the Bug it files;
    the id of that Bug.

    The Bug, of the kind given, takes the next id among the rows of its kind; it amends the work
    item, observes the text and expects what the work item expected, under the parent join
    gives. It is saved first, then the work item, which stays completed. Raises the refusals of
    the answer yes before anything is saved.
    """
    item = load_work_item(item_id)
    on = now()
    verified = verified_work_item(item, text, on, "no")
    named = work_item_id_text(item_id)
    added = add_work_item(
        kind=bug,
        title=f"No at the verify of {named}: {item.title}",
        criterion=make_defect(text, _expected_of(verified)),
        description="",
        find_work_item_rows=find_bug_rows,
        save_work_item=save_work_item,
        now=lambda: on,
        parent=join(verified.parent),
        amends=item_id,
    )
    save_work_item(verified)
    return added
