"""The text fgraph writes for the record: its items by bucket.

The text of one item whole is in flowgraph.status.show.
"""

from collections.abc import Collection, Iterable, Sequence
from typing import assert_never

from flowgraph.feature import FeatureRow
from flowgraph.story import StoryRow
from flowgraph.task import TaskRow
from flowgraph.upkeep import UpkeepRow
from flowgraph.work_item import STARTED, WorkItemRow

# The buckets of the flow in their order, each with the states of an item shown in it.
BUCKETS: Sequence[tuple[str, Collection[str]]] = (
    ("Backlog", frozenset({"backlog"})),
    ("InProgress", frozenset({"started", "blocked"})),
    ("Completed", frozenset({"completed"})),
    ("Removed", frozenset({"removed"})),
)

# The bucket that stands apart from the flow: listed by status only when it holds an item.
APART = "Removed"

# The state of a blocked Task: shown in InProgress, as blocked.
BLOCKED = "blocked"

# The state of a completed Task, as the record writes it.
COMPLETED = "completed"

# What ends a line cut to the width of the terminal.
CUT = "..."


def status_text(rows: Iterable[WorkItemRow | FeatureRow], top: int | None = None) -> str:
    """The items by bucket, in the order of the flow: a heading with its count, then its items.

    A completed item is listed with its commit when it holds one, a removed one with its reason.
    Removed stands apart from the flow: its heading is listed only when an item is removed. A
    Feature is one item of its bucket, listed among the work items in the order given. Under a
    top a heading lists that many of its items, the first ones given, then how many more it
    holds; its count stays that of all of them.
    """
    listed = list(rows)
    lines: list[str] = []
    for bucket, states in BUCKETS:
        held = [_item_lines(row) for row in listed if _is_listed_in(row, bucket, states)]
        if bucket == APART and not held:
            continue
        lines.append(f"{bucket} ({len(held)})\n")
        lines.extend(_top_of(held, top))
    return "".join(lines)


def cut_lines(text: str, width: int | None) -> str:
    """The text with each line longer than the width cut to it, ending with `...`.

    Without a width every line is whole. A width under that of the mark leaves the mark alone.
    """
    if width is None:
        return text
    keep = max(width - len(CUT), 0)
    lines = (line if len(line) <= width else f"{line[:keep]}{CUT}" for line in text.splitlines())
    return "".join(f"{line}\n" for line in lines)


def _is_listed_in(row: WorkItemRow | FeatureRow, bucket: str, states: Collection[str]) -> bool:
    """True when the bucket of those states lists the row: a Feature by the bucket of its row."""
    match row:
        case FeatureRow():
            return row.bucket == bucket
        case WorkItemRow():
            return row.state in states
        case _ as unreachable:
            assert_never(unreachable)


def _item_lines(row: WorkItemRow | FeatureRow) -> str:
    """One item of a bucket in the lines it is written in: a work item, or a Feature."""
    match row:
        case FeatureRow():
            return _feature_lines(row)
        case WorkItemRow():
            return _status_line(row)
        case _ as unreachable:
            assert_never(unreachable)


def _feature_lines(feature: FeatureRow) -> str:
    """One Feature: its id, its work items completed of all, then its title.

    A completed one is listed with its commit before its title, as a completed work item is,
    after the progress every line of a Feature holds right after its id. Under it each started
    work item of it, written as one of a bucket is with its Tasks being worked, two columns
    further in. A blocked one is marked `!` before its id and ends with what it waits on. So is
    one whose started work item holds a blocked Task, with what the first such Task waits on, as
    the line of that Task does: read from the rows at each listing, and kept nowhere. The block
    of the Feature itself comes before that of a Task. A removed one is listed as a removed work
    item is, its reason ending the line, without the progress: it holds no work item any more.
    """
    if feature.reason:
        return f"  {feature.id}  {feature.title}  -- {feature.reason}\n"
    progress = f"{feature.completed}/{feature.held} W"
    commit = f"{feature.commit}  " if feature.commit else ""
    started = (line for row in feature.started for line in _status_line(row).splitlines())
    under = "".join(f"  {line}\n" for line in started)
    line = f"{feature.id}  {progress}  {commit}{feature.title}"
    return f"{_marked(line, feature.waiting_on or _waited_on(feature.started))}\n{under}"


def _marked(line: str, waiting_on: str) -> str:
    """The line of an item of a bucket: marked `!` and ending with what it waits on, if any."""
    return f"! {line}  -- waiting on {waiting_on}" if waiting_on else f"  {line}"


def _waited_on(rows: Iterable[StoryRow | UpkeepRow]) -> str:
    """What the first blocked Task of the work items waits on; empty when none is blocked."""
    blocked = (task.waiting_on for row in rows for task in row.tasks if task.state == BLOCKED)
    return next(blocked, "")


def _top_of(items: Sequence[str], top: int | None) -> list[str]:
    """The first items up to the top, then how many more there are; every item without a top.

    An item is counted once, whatever the lines it is written in: a work item with its Tasks
    being worked, a Feature with its started work items.
    """
    if top is None or len(items) <= top:
        return list(items)
    return [*items[:top], f"  ... {len(items) - top} more\n"]


def _status_line(row: StoryRow | UpkeepRow) -> str:
    """One item of a bucket: its id and title, with its commit or the reason it was removed.

    A started one is listed with its Tasks completed of all, between its id and its title, and
    under it each Task of it being worked on a line of its own, in the order written. A completed
    one holds a commit or not: one it holds stands before the title, so a line cut to a width
    keeps it; a reason ends the line.
    """
    if row.state == STARTED:
        completed = sum(task.state == COMPLETED for task in row.tasks)
        worked = "".join(_task_line(task) for task in row.tasks)
        return f"  {row.id}  {completed}/{len(row.tasks)} T  {row.title}\n{worked}"
    if row.commit:
        return f"  {row.id}  {row.commit}  {row.title}\n"
    why = ", ".join(
        part
        for part in (f"superseded by {row.superseded_by}" if row.superseded_by else "", row.reason)
        if part
    )
    if why:
        return f"  {row.id}  {row.title}  -- {why}\n"
    return f"  {row.id}  {row.title}\n"


def _task_line(task: TaskRow) -> str:
    """A Task being worked, under its work item; nothing for one in Backlog or completed.

    A started Task is marked `=>`, a blocked one `!` and ends with what it waits on.
    """
    if task.state == STARTED:
        return f"    => {task.id}  {task.title}\n"
    if task.state == BLOCKED:
        return f"    !  {task.id}  {task.title}  -- waiting on {task.waiting_on}\n"
    return ""
