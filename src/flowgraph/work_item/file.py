"""The file of a work item in the record: one TOML file per item, named by its id, its Tasks inside.

A kind reads the files of its own prefix; a file of another prefix is left alone. The work item
and the primitives its file holds are built from each other in flowgraph.work_item.primitives.
"""

import tomllib
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from flowgraph.criterion import CommitError, CriterionError, DecisionError, EmptyPartError
from flowgraph.item import NoOffsetError, task_row, write_checked
from flowgraph.knowledge import KnowledgeRow
from flowgraph.parent import FeatureIdError, RealizesError
from flowgraph.record import ITEMS
from flowgraph.relation import RelationError
from flowgraph.task import TaskInProgressError
from flowgraph.work_item.agent import AgentError
from flowgraph.work_item.held_file import (
    HELD_ITEM,
    HeldItemFile,
    agent_held,
    block_held,
    commit_held,
    completed_held,
    reason_held,
    started_held,
    superseded_held,
    verified_held,
)
from flowgraph.work_item.id import (
    Kind,
    WorkItemId,
    WorkItemIdError,
    parse_work_item_id,
    work_item_id_text,
)
from flowgraph.work_item.model import (
    WorkItemFileError,
    WorkItemMismatchError,
    WorkItemNotFoundError,
    WorkItemState,
)
from flowgraph.work_item.primitives import item_held, item_primitives
from flowgraph.work_item.views import DependsRow, VerifiedRow, WorkItemDetail, WorkItemRow


def _read_file(path: Path, kind: Kind) -> HeldItemFile:
    """The content of one file of a work item of that kind; raises WorkItemFileError naming it.

    A time with no offset is refused so.
    """
    try:
        return HELD_ITEM.validate_python(tomllib.loads(path.read_text(encoding="utf-8")))
    except (tomllib.TOMLDecodeError, ValidationError, NoOffsetError) as error:
        raise WorkItemFileError(f"{path} holds no {kind.noun}: {error}") from error


def _files_of(record: Path, kind: Kind) -> list[HeldItemFile]:
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
            commit_held(held),
            reason_held(held),
            held.parent,
            complexity=held.complexity or "",
            created=held.created,
            started=started_held(held),
            agent=agent_held(held),
            block_reason=block_held(held)[0],
            waiting_on=block_held(held)[1],
            completed=completed_held(held),
            tasks=[task_row(task) for task in held.tasks],
            depends_on=held.depends_on,
            filed_during=held.filed_during,
            superseded_by=superseded_held(held),
            amends=held.amends,
        )
        for held in _files_of(record, kind)
    ]
    return sorted(rows, key=lambda row: parse_work_item_id(kind, row.id).number)


def read_work_item(record: Path, item_id: WorkItemId, kinds: Sequence[Kind] = ()) -> WorkItemState:
    """Adapter: the work item of that id in the record, whole.

    The ids it depends on are read as those of its own kind or of the kinds given. Raises
    WorkItemNotFoundError when the record holds no such item and WorkItemFileError when its file
    does not hold one, as when it holds more than one started Task, the criterion of another
    kind, a commit that is no sha, an agent that is none, an id it depends on that is of no kind
    or a blank title or reason.
    """
    path = _held_path(record, item_id)
    held = _read_file(path, item_id.kind)
    try:
        return item_held(held, item_id.kind, kinds)
    except (
        AgentError,
        TaskInProgressError,
        CriterionError,
        DecisionError,
        FeatureIdError,
        RealizesError,
        CommitError,
        WorkItemIdError,
        RelationError,
        EmptyPartError,
    ) as error:
        raise WorkItemFileError(f"{path} holds no {item_id.kind.noun}: {error}") from error


def read_work_item_detail(record: Path, item_id: WorkItemId) -> WorkItemDetail:
    """Adapter: the work item of that id in the record, with its Tasks, as plain data.

    Raises WorkItemNotFoundError when the record holds no such item and WorkItemFileError when
    its file does not hold one.
    """
    held = _read_file(_held_path(record, item_id), item_id.kind)
    answer = verified_held(held)
    block_reason, waiting_on = block_held(held)
    return WorkItemDetail(
        id=held.id,
        title=held.title,
        state=held.state,
        description=held.description,
        tasks=[task_row(task) for task in held.tasks],
        commit=commit_held(held),
        agent=agent_held(held),
        reason=block_reason or reason_held(held),
        waiting_on=waiting_on,
        parent=held.parent,
        complexity=held.complexity or "",
        knowledge=[
            KnowledgeRow(line.kind, line.noted, line.text, line.about, line.governs)
            for line in held.knowledge
        ],
        about=held.about,
        depends_on=[DependsRow(each) for each in held.depends_on],
        filed_during=held.filed_during,
        superseded_by=superseded_held(held),
        amends=held.amends,
        verified=None if answer is None else VerifiedRow(answer.answer, answer.text, answer.on),
        **held.criterion.model_dump(),
    )


def read_task_ids(record: Path, kind: Kind) -> list[str]:
    """Adapter: the ids of every Task of the work items of that kind in the record, in no order.

    Raises WorkItemFileError naming the first file of the kind that does not hold one.
    """
    return [task.id for held in _files_of(record, kind) for task in held.tasks]


def write_work_item(record: Path, item: WorkItemState, kinds: Sequence[Kind] = ()) -> None:
    """Adapter: write the work item as its one file in the record.

    The item is written beside its file and read back before it replaces it, the ids it depends
    on as those of its own kind or of the kinds given. Raises
    WorkItemMismatchError naming the file when the item read back differs; the file is then as
    it was before.
    """
    kind = item.id.kind
    path = work_item_path(record, item.id)
    write_checked(
        path,
        item_primitives(item),
        lambda beside: item_held(_read_file(beside, kind), kind, kinds) == item,
        WorkItemMismatchError(f"{path}: the {kind.noun} written reads back different"),
    )
