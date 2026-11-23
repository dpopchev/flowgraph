"""The commands of a work item: each loads it whole, moves it, saves it.

The row and the detail a view reads are in flowgraph.work_item.projection, the commands on a Task
of a work item in flowgraph.work_item.task_commands.
"""

from collections.abc import Iterable

from flowgraph.criterion import Criterion
from flowgraph.knowledge import KnowledgeKind, make_knowledge_line
from flowgraph.parent import STANDALONE, Parent
from flowgraph.record import Now
from flowgraph.work_item.agent import Agent
from flowgraph.work_item.amend import Amendment, CheckMove, amended_work_item
from flowgraph.work_item.complexity import Complexity
from flowgraph.work_item.handed import handed_work_item
from flowgraph.work_item.id import (
    Kind,
    WorkItemId,
    next_work_item_id,
    parse_work_item_id,
)
from flowgraph.work_item.model import (
    FindWorkItemRows,
    LoadWorkItem,
    SaveWorkItem,
    make_work_item,
    noted_work_item,
)
from flowgraph.work_item.moves import started_work_item
from flowgraph.work_item.removal import removed_work_item


def add_work_item(
    *,
    kind: Kind,
    title: str,
    criterion: Criterion,
    description: str,
    find_work_item_rows: FindWorkItemRows,
    save_work_item: SaveWorkItem,
    now: Now,
    parent: Parent = STANDALONE,
    depends_on: Iterable[WorkItemId] = (),
    filed_during: WorkItemId | None = None,
    amends: WorkItemId | None = None,
    about: tuple[str, ...] = (),
    complexity: Complexity | None = None,
) -> WorkItemId:
    """Add a work item of that kind to Backlog under its next free id and return that id.

    It stands alone unless a Feature is named as its parent, depends on the work items given,
    is filed during the one given, amends the one given, is about the terms given and carries the
    complexity given, none by default. The rows
    found are those of the kind. Raises EmptyPartError when the title is blank and CriterionError
    when the criterion is not of the form the kind takes; nothing is saved.
    """
    taken = [parse_work_item_id(kind, row.id) for row in find_work_item_rows()]
    item_id = next_work_item_id(kind, taken)
    item = make_work_item(
        item_id,
        title,
        criterion,
        description,
        now(),
        parent,
        depends_on,
        filed_during,
        amends,
        about,
        complexity,
    )
    save_work_item(item)
    return item.id


def remove_work_item(
    *,
    item_id: WorkItemId,
    reason: str,
    load_work_item: LoadWorkItem,
    save_work_item: SaveWorkItem,
    now: Now,
    superseded_by: WorkItemId | None = None,
) -> None:
    """Remove the work item in Backlog of that id now, for the reason, and save it whole.

    It names the work item that supersedes it when one is given. Raises WorkItemNotFoundError
    when the record holds no such item, EmptyPartError when the reason is blank with none named,
    StartedAlreadyError when the item is started, CompletedAlreadyError when it is completed,
    RemovedAlreadyError when it is removed and RelationError when it names itself; nothing is
    saved.
    """
    save_work_item(removed_work_item(load_work_item(item_id), reason, now(), superseded_by))


def amend_work_item(
    *,
    item_id: WorkItemId,
    amendment: Amendment,
    load_work_item: LoadWorkItem,
    save_work_item: SaveWorkItem,
    check_move: CheckMove,
) -> None:
    """Rewrite the parts the amendment names of the work item of that id and save it whole.

    A parent named that is not the one it has is a move, checked through check_move before the
    save. Raises WorkItemNotFoundError when the record holds no such item, NoPartError when the
    amendment names no part, EmptyPartError when the title or a part of the criterion is blank,
    StartedAlreadyError when the item is started, CompletedAlreadyError when it is completed
    and the refusal of the check; nothing is saved.
    """
    was = load_work_item(item_id)
    amended = amended_work_item(was, amendment)
    if amended.parent != was.parent:
        check_move(item_id, was.parent, amended.parent)
    save_work_item(amended)


def start_work_item(
    *,
    item_id: WorkItemId,
    load_work_item: LoadWorkItem,
    save_work_item: SaveWorkItem,
    now: Now,
    agent: Agent | None = None,
) -> None:
    """Start the work item of that id now, handed to the agent when one is given, and save it.

    Raises WorkItemNotFoundError when the record holds no such item, NoTaskError when it has no
    Task, StartedAlreadyError when it is started and CompletedAlreadyError when it is completed;
    nothing is saved.
    """
    begun = started_work_item(load_work_item(item_id), now())
    save_work_item(handed_work_item(begun, agent))


def note_work_item(
    *,
    item_id: WorkItemId,
    kind: KnowledgeKind,
    text: str,
    load_work_item: LoadWorkItem,
    save_work_item: SaveWorkItem,
    now: Now,
    about: tuple[str, ...] = (),
    governs: tuple[str, ...] = (),
) -> None:
    """Keep a line of that kind and text on the work item of that id, in any state, and save it.

    The line is about the terms given, governs the files given and goes after the lines the item
    keeps. Raises
    WorkItemNotFoundError when the record holds no such item and EmptyPartError when the text is
    blank; nothing is saved.
    """
    line = make_knowledge_line(kind, text, now(), about, governs)
    save_work_item(noted_work_item(load_work_item(item_id), line))
