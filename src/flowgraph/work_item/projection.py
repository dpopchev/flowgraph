"""The projections of a work item: the row and the detail a view reads, each a pure map of it.

The commands that move a work item are in flowgraph.work_item.commands.
"""

from datetime import datetime
from typing import assert_never

from flowgraph.criterion import criterion_parts
from flowgraph.knowledge import knowledge_row
from flowgraph.parent import parent_text
from flowgraph.task import row_of
from flowgraph.work_item.block import block_of
from flowgraph.work_item.handed import agent_text
from flowgraph.work_item.id import WorkItemId, work_item_id_text
from flowgraph.work_item.model import (
    BlockedWorkItem,
    CompletedWorkItem,
    RemovedWorkItem,
    StartedWorkItem,
    WorkItem,
    WorkItemState,
)
from flowgraph.work_item.progress import progress_row
from flowgraph.work_item.removal import reason_of, superseded_by_of
from flowgraph.work_item.state import commit_sha, state_name
from flowgraph.work_item.verification import Verification
from flowgraph.work_item.views import DependsRow, VerifiedRow, WorkItemDetail, WorkItemRow


def _started_on(item: WorkItemState) -> datetime | None:
    """The started time of a started or blocked work item; none in any other, as its file reads."""
    match item:
        case StartedWorkItem() | BlockedWorkItem():
            return item.started
        case WorkItem() | CompletedWorkItem() | RemovedWorkItem():
            return None
        case _ as unreachable:
            assert_never(unreachable)


def _completed_on(item: WorkItemState) -> datetime | None:
    """The completed time of a completed work item; none for one not completed."""
    match item:
        case CompletedWorkItem():
            return item.completed
        case WorkItem() | StartedWorkItem() | BlockedWorkItem() | RemovedWorkItem():
            return None
        case _ as unreachable:
            assert_never(unreachable)


def _named_text(named: WorkItemId | None) -> str:
    """The id of the work item another one names as written; empty for none."""
    return "" if named is None else work_item_id_text(named)


def _verified_row(item: WorkItemState) -> VerifiedRow | None:
    """The answer of the closing of a completed work item as a row; none for any other."""
    match item:
        case CompletedWorkItem(verified=Verification() as answer):
            return VerifiedRow(answer.answer, answer.text, answer.on)
        case _:
            return None


def work_item_row(item: WorkItemState) -> WorkItemRow:
    """The work item as the row a view reads, whole: the row its file is read as."""
    return WorkItemRow(
        work_item_id_text(item.id),
        item.title,
        state_name(item),
        commit_sha(item),
        reason_of(item),
        parent_text(item.parent),
        complexity=item.complexity or "",
        created=item.created,
        started=_started_on(item),
        agent=agent_text(item),
        block_reason=block_of(item)[0],
        waiting_on=block_of(item)[1],
        completed=_completed_on(item),
        tasks=[row_of(task) for task in item.tasks],
        depends_on=[work_item_id_text(each) for each in item.relations.depends_on],
        filed_during=_named_text(item.relations.filed_during),
        superseded_by=superseded_by_of(item),
        amends=_named_text(item.relations.amends),
    )


def work_item_detail(item: WorkItemState) -> WorkItemDetail:
    """The work item with its criterion and its Tasks as the plain data a view reads."""
    block_reason, waiting_on = block_of(item)
    return WorkItemDetail(
        id=work_item_id_text(item.id),
        title=item.title,
        state=state_name(item),
        description=item.description,
        tasks=[row_of(task) for task in item.tasks],
        commit=commit_sha(item),
        agent=agent_text(item),
        reason=block_reason or reason_of(item),
        waiting_on=waiting_on,
        parent=parent_text(item.parent),
        complexity=item.complexity or "",
        knowledge=[knowledge_row(line) for line in item.knowledge],
        about=list(item.about),
        depends_on=[DependsRow(work_item_id_text(each)) for each in item.relations.depends_on],
        filed_during=_named_text(item.relations.filed_during),
        filed_here=[],
        superseded_by=superseded_by_of(item),
        supersedes=[],
        amends=_named_text(item.relations.amends),
        amended_by=[],
        verified=_verified_row(item),
        progress=[progress_row(line) for line in item.progress],
        **criterion_parts(item.criterion),
    )
