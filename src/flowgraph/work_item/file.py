"""The file of a work item in the record: one TOML file per item, named by its id, its Tasks inside.

A kind reads the files of its own prefix; a file of another prefix is left alone.
"""

import tomllib
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, assert_never

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from flowgraph.criterion import CommitError, CriterionError, DecisionError, evidence_written
from flowgraph.item_file import (
    AnyCriterionFile,
    CompletedTaskFile,
    HeldTask,
    KnowledgeFile,
    TaskFile,
    backlog_task,
    criterion_held,
    criterion_primitives,
    decision_held,
    evidence_primitives,
    knowledge_held,
    knowledge_primitives,
    task_held,
    task_primitives,
    task_row,
    write_checked,
)
from flowgraph.knowledge import KnowledgeRow
from flowgraph.parent import FeatureIdError, parent_text, parent_written
from flowgraph.record import ITEMS
from flowgraph.task import TaskInProgressError
from flowgraph.task_list import at_most_one_started
from flowgraph.work_item.model import (
    CompletedWorkItem,
    Kind,
    RemovedWorkItem,
    StartedWorkItem,
    WorkItem,
    WorkItemFileError,
    WorkItemId,
    WorkItemMismatchError,
    WorkItemNotFoundError,
    WorkItemState,
    append_task,
    completed_work_item,
    make_work_item,
    parse_work_item_id,
    started_work_item,
    state_name,
    work_item_id_text,
)
from flowgraph.work_item.removal import removed_work_item
from flowgraph.work_item.views import WorkItemDetail, WorkItemRow


class _ItemFile(BaseModel):
    """What the file of a work item in Backlog holds: its Tasks are all in Backlog."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["backlog"]
    title: str
    description: str = ""
    parent: str = ""
    created: datetime
    criterion: AnyCriterionFile
    tasks: list[TaskFile] = []
    knowledge: list[KnowledgeFile] = []


class _StartedItemFile(BaseModel):
    """What the file of a started work item holds: its started time, its Tasks in any state."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["started"]
    title: str
    description: str = ""
    parent: str = ""
    created: datetime
    started: datetime
    criterion: AnyCriterionFile
    tasks: list[HeldTask] = []
    knowledge: list[KnowledgeFile] = []


class _CompletedItemFile(BaseModel):
    """What the file of a completed work item holds: the commit it has, its Tasks all completed."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["completed"]
    title: str
    description: str = ""
    parent: str = ""
    created: datetime
    started: datetime
    completed: datetime
    commit: str = ""
    criterion: AnyCriterionFile
    tasks: list[CompletedTaskFile] = []
    knowledge: list[KnowledgeFile] = []


class _RemovedItemFile(BaseModel):
    """What the file of a removed work item holds: its removal, its Tasks all in Backlog."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["removed"]
    title: str
    description: str = ""
    parent: str = ""
    created: datetime
    removed: datetime
    reason: str
    criterion: AnyCriterionFile
    tasks: list[TaskFile] = []
    knowledge: list[KnowledgeFile] = []


# The file of a work item in any of its states.
_HeldItemFile = _ItemFile | _StartedItemFile | _CompletedItemFile | _RemovedItemFile

# The validator of a work item file, which tells the states apart by the state line.
_HELD_ITEM: TypeAdapter[_HeldItemFile] = TypeAdapter(
    Annotated[_HeldItemFile, Field(discriminator="state")]
)


def _commit_held(held: _HeldItemFile) -> str:
    """The commit a validated file holds; empty for an item that has none."""
    match held:
        case _CompletedItemFile():
            return held.commit
        case _ItemFile() | _StartedItemFile() | _RemovedItemFile():
            return ""
        case _ as unreachable:
            assert_never(unreachable)


def _reason_held(held: _HeldItemFile) -> str:
    """The reason a validated file holds; empty for an item not removed."""
    match held:
        case _RemovedItemFile():
            return held.reason
        case _ItemFile() | _StartedItemFile() | _CompletedItemFile():
            return ""
        case _ as unreachable:
            assert_never(unreachable)


def _started_held(held: _HeldItemFile) -> datetime | None:
    """The started time a validated file of a started item holds; none in any other state."""
    match held:
        case _StartedItemFile():
            return held.started
        case _ItemFile() | _CompletedItemFile() | _RemovedItemFile():
            return None
        case _ as unreachable:
            assert_never(unreachable)


def _completed_held(held: _HeldItemFile) -> datetime | None:
    """The completed time a validated file holds; none for an item not completed."""
    match held:
        case _CompletedItemFile():
            return held.completed
        case _ItemFile() | _StartedItemFile() | _RemovedItemFile():
            return None
        case _ as unreachable:
            assert_never(unreachable)


def _read_file(path: Path, kind: Kind) -> _HeldItemFile:
    """The content of one file of a work item of that kind; raises WorkItemFileError naming it."""
    try:
        return _HELD_ITEM.validate_python(tomllib.loads(path.read_text(encoding="utf-8")))
    except (tomllib.TOMLDecodeError, ValidationError) as error:
        raise WorkItemFileError(f"{path} holds no {kind.noun}: {error}") from error


def _files_of(record: Path, kind: Kind) -> list[_HeldItemFile]:
    """The content of every file of a work item of that kind in the record, in no order."""
    return [_read_file(path, kind) for path in (record / ITEMS).glob(f"{kind.prefix}-*.toml")]


def work_item_path(record: Path, item_id: WorkItemId) -> Path:
    """The path of the file of the work item of that id in the record, whether or not it exists.

    The one place that says where a work item is kept: named by its id, under `items/`.
    """
    return record / ITEMS / f"{work_item_id_text(item_id)}.toml"


def _held_path(record: Path, item_id: WorkItemId) -> Path:
    """The file of the work item of that id; raises WorkItemNotFoundError without one."""
    path = work_item_path(record, item_id)
    if not path.is_file():
        raise WorkItemNotFoundError(item_id)
    return path


def read_work_item_rows(record: Path, kind: Kind) -> list[WorkItemRow]:
    """Adapter: the rows of the work items of that kind in the record, by id, each with its Tasks.

    Raises WorkItemFileError naming the first file of the kind that does not hold one.
    """
    rows = [
        WorkItemRow(
            held.id,
            held.title,
            held.state,
            _commit_held(held),
            _reason_held(held),
            held.parent,
            created=held.created,
            started=_started_held(held),
            completed=_completed_held(held),
            tasks=[task_row(task) for task in held.tasks],
        )
        for held in _files_of(record, kind)
    ]
    return sorted(rows, key=lambda row: parse_work_item_id(kind, row.id).number)


def read_work_item(record: Path, item_id: WorkItemId) -> WorkItemState:
    """Adapter: the work item of that id in the record, whole.

    Raises WorkItemNotFoundError when the record holds no such item and WorkItemFileError when
    its file does not hold one, as when it holds more than one started Task, the criterion of
    another kind or a commit that is no sha.
    """
    path = _held_path(record, item_id)
    held = _read_file(path, item_id.kind)
    try:
        return _item_held(held, item_id.kind)
    except (
        TaskInProgressError,
        CriterionError,
        DecisionError,
        FeatureIdError,
        CommitError,
    ) as error:
        raise WorkItemFileError(f"{path} holds no {item_id.kind.noun}: {error}") from error


def read_work_item_detail(record: Path, item_id: WorkItemId) -> WorkItemDetail:
    """Adapter: the work item of that id in the record, with its Tasks, as plain data.

    Raises WorkItemNotFoundError when the record holds no such item and WorkItemFileError when
    its file does not hold one.
    """
    held = _read_file(_held_path(record, item_id), item_id.kind)
    return WorkItemDetail(
        id=held.id,
        title=held.title,
        state=held.state,
        description=held.description,
        tasks=[task_row(task) for task in held.tasks],
        commit=_commit_held(held),
        reason=_reason_held(held),
        parent=held.parent,
        knowledge=[KnowledgeRow(line.kind, line.noted, line.text) for line in held.knowledge],
        **held.criterion.model_dump(),
    )


def read_task_ids(record: Path, kind: Kind) -> list[str]:
    """Adapter: the ids of every Task of the work items of that kind in the record, in no order.

    Raises WorkItemFileError naming the first file of the kind that does not hold one.
    """
    return [task.id for held in _files_of(record, kind) for task in held.tasks]


def _moves_primitives(item: WorkItemState) -> dict[str, object]:
    """The times and the commit of the moves an item has made, as its file holds them."""
    match item:
        case WorkItem():
            return {}
        case StartedWorkItem():
            return {"started": item.started}
        case CompletedWorkItem():
            times = {"started": item.started, "completed": item.completed}
            return {**times, **evidence_primitives(item.commit)}
        case RemovedWorkItem():
            return {"removed": item.removed, "reason": item.reason}
        case _ as unreachable:
            assert_never(unreachable)


def _item_primitives(item: WorkItemState) -> dict[str, object]:
    """The work item as the primitives its file holds.

    A description, a parent, a commit and tasks are held only when there is one: a work item
    that stands alone is written without a parent, one completed without a commit without one.
    """
    described = {"description": item.description} if item.description else {}
    under = {"parent": parent_text(item.parent)} if parent_text(item.parent) else {}
    tasks = {"tasks": [task_primitives(task) for task in item.tasks]} if item.tasks else {}
    lines = [knowledge_primitives(line) for line in item.knowledge]
    knowledge = {"knowledge": lines} if lines else {}
    return {
        "id": work_item_id_text(item.id),
        "state": state_name(item),
        "title": item.title,
        **described,
        **under,
        "created": item.created,
        **_moves_primitives(item),
        "criterion": criterion_primitives(item.criterion),
        **tasks,
        **knowledge,
    }


def _item_held(held: _HeldItemFile, kind: Kind) -> WorkItemState:
    """The work item of that kind a validated file holds, built through its constructors.

    An item and its Tasks past Backlog are built by the moves that took them there, so a file
    holds no state those moves could not reach. Raises TaskInProgressError when it holds more
    than one started Task, CriterionError when it holds the criterion of another kind or a
    decision before it is completed, and DecisionError when its completion lacks its decision.
    """
    criterion = criterion_held(held.criterion)
    decision = decision_held(held.criterion)
    if decision is not None and not isinstance(held, _CompletedItemFile):
        raise CriterionError(f"{kind.article} {kind.noun} holds its decision once it is completed")
    item_id = parse_work_item_id(kind, held.id)
    parent = parent_written(held.parent)
    item = make_work_item(item_id, held.title, criterion, held.description, held.created, parent)
    for task in held.tasks:
        item = append_task(item, backlog_task(task))
    item = replace(item, knowledge=tuple(knowledge_held(line) for line in held.knowledge))
    match held:
        case _ItemFile():
            return item
        case _RemovedItemFile():
            return removed_work_item(item, held.reason, held.removed)
        case _StartedItemFile() | _CompletedItemFile():
            tasks = at_most_one_started(tuple(task_held(task) for task in held.tasks))
            begun = replace(started_work_item(item, held.started), tasks=tasks)
            match held:
                case _CompletedItemFile():
                    commit = evidence_written(held.commit)
                    return completed_work_item(begun, held.completed, commit, decision)
                case _StartedItemFile():
                    return begun
                case _ as unreachable:
                    assert_never(unreachable)
        case _ as unreachable:
            assert_never(unreachable)


def write_work_item(record: Path, item: WorkItemState) -> None:
    """Adapter: write the work item as its one file in the record.

    The item is written beside its file and read back before it replaces it. Raises
    WorkItemMismatchError naming the file when the item read back differs; the file is then as
    it was before.
    """
    kind = item.id.kind
    path = work_item_path(record, item.id)
    write_checked(
        path,
        _item_primitives(item),
        lambda beside: _item_held(_read_file(beside, kind), kind) == item,
        WorkItemMismatchError(f"{path}: the {kind.noun} written reads back different"),
    )
