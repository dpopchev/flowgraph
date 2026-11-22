"""A work item and the primitives its file holds: each built from the other, through the moves."""

from collections.abc import Sequence
from dataclasses import replace
from typing import assert_never

from flowgraph.criterion import Answer, CriterionError, evidence_written
from flowgraph.item import (
    backlog_task,
    criterion_held,
    criterion_primitives,
    decision_held,
    evidence_primitives,
    knowledge_held,
    knowledge_primitives,
    task_held,
    task_primitives,
)
from flowgraph.parent import parent_text, parent_written
from flowgraph.task import at_most_one_started
from flowgraph.work_item.depends import id_held, relations_held, relations_primitives
from flowgraph.work_item.held_file import (
    CompletedItemFile,
    HeldItemFile,
    ItemFile,
    RemovedItemFile,
    StartedItemFile,
)
from flowgraph.work_item.id import Kind, parse_work_item_id, work_item_id_text
from flowgraph.work_item.model import (
    CompletedWorkItem,
    RemovedWorkItem,
    StartedWorkItem,
    WorkItem,
    WorkItemState,
    append_task,
    make_work_item,
    state_name,
)
from flowgraph.work_item.moves import completed_work_item, started_work_item
from flowgraph.work_item.removal import removed_work_item
from flowgraph.work_item.verification import make_verification


def _verified_primitives(item: CompletedWorkItem) -> dict[str, object]:
    """The answer of the closing as its table, held only once the item has one."""
    answer = item.verified
    if answer is None:
        return {}
    return {"verified": {"answer": answer.answer, "text": answer.text, "on": answer.on}}


def _moves_primitives(item: WorkItemState) -> dict[str, object]:
    """The times and the commit of the moves an item has made, as its file holds them."""
    match item:
        case WorkItem():
            return {}
        case StartedWorkItem():
            return {"started": item.started}
        case CompletedWorkItem():
            times = {"started": item.started, "completed": item.completed}
            return {**times, **evidence_primitives(item.commit), **_verified_primitives(item)}
        case RemovedWorkItem():
            named = item.superseded_by
            superseded = {} if named is None else {"superseded_by": work_item_id_text(named)}
            return {"removed": item.removed, "reason": item.reason, **superseded}
        case _ as unreachable:
            assert_never(unreachable)


def item_primitives(item: WorkItemState) -> dict[str, object]:
    """The work item as the primitives its file holds.

    A description, a parent, a commit and tasks are held only when there is one: a work item
    that stands alone is written without a parent, one completed without a commit without one.
    """
    described = {"description": item.description} if item.description else {}
    under = {"parent": parent_text(item.parent)} if parent_text(item.parent) else {}
    tasks = {"tasks": [task_primitives(task) for task in item.tasks]} if item.tasks else {}
    lines = [knowledge_primitives(line) for line in item.knowledge]
    knowledge = {"knowledge": lines} if lines else {}
    about = {"about": list(item.about)} if item.about else {}
    return {
        "id": work_item_id_text(item.id),
        "state": state_name(item),
        "title": item.title,
        **described,
        **under,
        **about,
        "created": item.created,
        **_moves_primitives(item),
        "criterion": criterion_primitives(item.criterion),
        **tasks,
        **knowledge,
        **relations_primitives(item.relations),
    }


def _verified(done: CompletedWorkItem, held: CompletedItemFile) -> CompletedWorkItem:
    """The completed work item with the answer its file holds, built through its constructor.

    Raises CriterionError when a Spike holds one and EmptyPartError when its text is blank.
    """
    if held.verified is None:
        return done
    if isinstance(done.criterion, Answer):
        raise CriterionError("a Spike holds no answer of a closing: fgraph verify takes none")
    answer = held.verified
    return replace(done, verified=make_verification(answer.answer, answer.text, answer.on))


def item_held(held: HeldItemFile, kind: Kind, kinds: Sequence[Kind] = ()) -> WorkItemState:
    """The work item of that kind a validated file holds, built through its constructors.

    An item and its Tasks past Backlog are built by the moves that took them there, so a file
    holds no state those moves could not reach. Raises TaskInProgressError when it holds more
    than one started Task, CriterionError when it holds the criterion of another kind or a
    decision before it is completed, DecisionError when its completion lacks its decision,
    WorkItemIdError when it depends on an id of none of the kinds and RelationError when on itself.
    """
    criterion = criterion_held(held.criterion)
    decision = decision_held(held.criterion)
    if decision is not None and not isinstance(held, CompletedItemFile):
        raise CriterionError(f"{kind.article} {kind.noun} holds its decision once it is completed")
    item_id = parse_work_item_id(kind, held.id)
    parent = parent_written(held.parent)
    about = tuple(held.about)
    item = make_work_item(
        item_id, held.title, criterion, held.description, held.created, parent, about=about
    )
    for task in held.tasks:
        item = append_task(item, backlog_task(task))
    relations = relations_held(item_id, held, (kind, *kinds))
    item = replace(item, knowledge=tuple(knowledge_held(line) for line in held.knowledge))
    item = replace(item, relations=relations)
    match held:
        case ItemFile():
            return item
        case RemovedItemFile():
            superseded_by = (
                id_held(held.superseded_by, (kind, *kinds)) if held.superseded_by else None
            )
            return removed_work_item(item, held.reason, held.removed, superseded_by)
        case StartedItemFile() | CompletedItemFile():
            tasks = at_most_one_started(tuple(task_held(task) for task in held.tasks))
            begun = replace(started_work_item(item, held.started), tasks=tasks)
            match held:
                case CompletedItemFile():
                    commit = evidence_written(held.commit)
                    done = completed_work_item(begun, held.completed, commit, decision)
                    return _verified(done, held)
                case StartedItemFile():
                    return begun
                case _ as unreachable:
                    assert_never(unreachable)
        case _ as unreachable:
            assert_never(unreachable)
