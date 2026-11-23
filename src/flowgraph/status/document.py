"""The JSON document of status: the buckets with every item of them, and the next to start.

A second formatter of the rows `flowgraph.status.view` lists, beside the text: no fact is
computed here. The document holds `buckets`, each with its `name`, its `count` and every one of
its `items`, in the order of the flow and of the rows given, and `next_to_start`, the id of the
line marked as such or null. A work item holds its `id`, `kind`, `title`, `state`, `commit`,
`reason` and `superseded_by` (null while empty), `progress` (its Tasks `completed` of `total`),
its `tasks` and the ids it `waits_for`. A work item holds its `complexity` too, the word or null.
A Task holds its `id`, `title`, `state`, `commit`, `reason` and `waiting_on`.
A Feature holds its `id`, `kind`, `title`, `commit`, `reason`,
`progress` (its work items `completed` of `total`), the ids its first work item `waits_for`, its
`block` -- the `reason` and what it is `waiting_on`, or null -- and its `work_items`: every work
item under it, in any state, shaped as a work item of a bucket, in the order `fgraph show` of
the Feature lists them. `can_start` lists the ids of every line marked as able to start now, in
order, and `next_to_start` is the first of them.
"""

import json
from collections.abc import Iterable
from typing import Any, assert_never

from flowgraph.feature import FeatureRow
from flowgraph.record.store import KINDS
from flowgraph.status.next import start_now_ids
from flowgraph.status.text import BUCKETS, is_listed_in
from flowgraph.task import TaskRow
from flowgraph.work_item import WorkItemRow

# The two formats of status; the first is the default.
TEXT = "text"
JSON = "json"

# The state of a completed Task, as the record writes it.
_COMPLETED = "completed"

type Row = WorkItemRow | FeatureRow
type Item = dict[str, Any]


class StatusFormatError(ValueError):
    """A format of status that is none there is."""


def chosen_format(format_: str) -> str:
    """The format of status asked for.

    Raises StatusFormatError naming the word and the two formats when it is neither.
    """
    if format_ not in (TEXT, JSON):
        raise StatusFormatError(
            f"--format {format_!r} is not {TEXT} or {JSON}, the two formats of status"
        )
    return format_


def status_json(rows: Iterable[Row]) -> str:
    """The document of the rows given: every bucket with its count and every item, as JSON.

    The keys are sorted and the text ends with a newline, so two runs on one record print the
    same bytes.
    """
    listed = list(rows)
    buckets = [
        {
            "name": bucket,
            "count": len(items),
            "items": [_item(row) for row in items],
        }
        for bucket, states in BUCKETS
        for items in [[row for row in listed if is_listed_in(row, bucket, states)]]
    ]
    can_start = start_now_ids(listed)
    document = {
        "buckets": buckets,
        "can_start": can_start,
        "next_to_start": can_start[0] if can_start else None,
    }
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def _item(row: Row) -> Item:
    """One item of a bucket: a work item, or a Feature."""
    match row:
        case FeatureRow():
            return _feature(row)
        case WorkItemRow():
            return _work_item(row)
        case _ as unreachable:
            assert_never(unreachable)


def _work_item(row: WorkItemRow) -> Item:
    """A work item with its Tasks; its kind is that of the prefix of its id."""
    kinds = {kind.prefix: kind.noun.lower() for kind in KINDS}
    return {
        "id": row.id,
        "kind": kinds[row.id.partition("-")[0]],
        "complexity": row.complexity or None,
        "title": row.title,
        "state": row.state,
        "commit": row.commit or None,
        "reason": row.reason or None,
        "superseded_by": row.superseded_by or None,
        "progress": {
            "completed": sum(task.state == _COMPLETED for task in row.tasks),
            "total": len(row.tasks),
        },
        "tasks": [_task(task) for task in row.tasks],
        "waits_for": list(row.waits_for),
    }


def _task(task: TaskRow) -> Item:
    """A Task with its state, and its reason and what it waits on while it is blocked."""
    return {
        "id": task.id,
        "title": task.title,
        "state": task.state,
        "commit": task.commit or None,
        "reason": task.reason or None,
        "waiting_on": task.waiting_on or None,
    }


def _feature(row: FeatureRow) -> Item:
    """A Feature with every work item under it; its block when it waits on someone."""
    block = {"reason": row.block_reason, "waiting_on": row.waiting_on} if row.waiting_on else None
    return {
        "id": row.id,
        "kind": "feature",
        "title": row.title,
        "commit": row.commit or None,
        "reason": row.reason or None,
        "progress": {"completed": row.completed, "total": row.held},
        "waits_for": list(row.waits_for),
        "block": block,
        "work_items": [_work_item(each) for each in row.work_items],
    }
