"""The text fgraph writes for the record: its items by bucket, and one item whole."""

from collections.abc import Collection, Iterable, Sequence
from typing import assert_never

from flowgraph.feature import FeatureDetail, FeatureRow
from flowgraph.story import StoryDetail, StoryRow
from flowgraph.task import TaskRow
from flowgraph.upkeep import UpkeepDetail, UpkeepRow
from flowgraph.work_item import WorkItemRow

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

# The states of a started work item or Task and of a completed Task, as the record writes them.
STARTED = "started"
COMPLETED = "completed"

# What ends a line cut to the width of the terminal.
CUT = "..."


def status_text(rows: Iterable[WorkItemRow | FeatureRow], top: int | None = None) -> str:
    """The items by bucket, in the order of the flow: a heading with its count, then its items.

    A completed item is listed with its commit, a removed one with its reason. Removed stands
    apart from the flow: its heading is listed only when an item is removed. A Feature is one
    item of its derived bucket, listed among the work items in the order given. Under a top a
    heading lists that many of its items, the first ones given, then how many more it holds;
    its count stays that of all of them.
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
    """True when the bucket of those states lists the row: a Feature by its derived bucket."""
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

    Under it each started work item of it, written as one of a bucket is with its Tasks being
    worked, two columns further in.
    """
    progress = f"{feature.completed}/{feature.held} W"
    started = (line for row in feature.started for line in _status_line(row).splitlines())
    under = "".join(f"  {line}\n" for line in started)
    return f"  {feature.id}  {progress}  {feature.title}\n{under}"


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
    under it each Task of it being worked on a line of its own, in the order written. A commit
    stands before the title, so a line cut to a width keeps it; a reason ends the line.
    """
    if row.state == STARTED:
        completed = sum(task.state == COMPLETED for task in row.tasks)
        worked = "".join(_task_line(task) for task in row.tasks)
        return f"  {row.id}  {completed}/{len(row.tasks)} T  {row.title}\n{worked}"
    if row.commit:
        return f"  {row.id}  {row.commit}  {row.title}\n"
    if row.reason:
        return f"  {row.id}  {row.title}  -- {row.reason}\n"
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


def feature_text(detail: FeatureDetail, rows: Iterable[StoryRow | UpkeepRow], bucket: str) -> str:
    """The Feature with its bucket, its criteria, then its work items with their buckets.

    The bucket of a Feature is derived, so it is given; a description is listed only when there
    is one.
    """
    listed = list(rows)
    described = [f"  description  {detail.description}\n"] if detail.description else []
    lines = [
        f"{detail.id}  {detail.title}\n",
        f"  bucket       {bucket}\n",
        *described,
        f"Criteria ({len(detail.criteria)})\n",
        *(f"  {criterion}\n" for criterion in detail.criteria),
        f"Work items ({len(listed)})\n",
    ]
    for row in listed:
        held_in = next(name for name, states in BUCKETS if row.state in states)
        lines.append(f"  {row.id}  {row.title}  {held_in}\n")
    return "".join(lines)


def show_text(detail: StoryDetail | UpkeepDetail) -> str:
    """The work item with its bucket and its criterion, then its Tasks, one fact per line.

    The criterion is listed by the parts its kind states: a Given / When / Then, what is
    observed and expected, or a hypothesis with, once it is answered, its decision under it.
    A parent, a description, a commit and the reason of a removal are listed only when there is
    one, the bucket of a Task only once it has left Backlog. A blocked Task is listed in
    InProgress as blocked, with its reason and what it waits on.
    """
    bucket = next(name for name, states in BUCKETS if detail.state in states)
    under = [f"  parent       {detail.parent}\n"] if detail.parent else []
    committed = [f"  commit       {detail.commit}\n"] if detail.commit else []
    removed = [f"  reason       {detail.reason}\n"] if detail.reason else []
    described = [f"  description  {detail.description}\n"] if detail.description else []
    stated = {
        "given": detail.given,
        "when": detail.when,
        "then": detail.then,
        "observed": detail.observed,
        "expected": detail.expected,
        "hypothesis": detail.hypothesis,
        "decision": detail.decision,
    }
    lines = [
        f"{detail.id}  {detail.title}\n",
        f"  bucket       {bucket}\n",
        *under,
        *committed,
        *removed,
        *described,
        *(f"  {part:<13}{text}\n" for part, text in stated.items() if text),
        f"Tasks ({len(detail.tasks)})\n",
    ]
    for task in detail.tasks:
        lines.append(f"  {task.id}  {task.title}\n")
        task_bucket = next(name for name, states in BUCKETS if task.state in states)
        if task.state == BLOCKED:
            lines.append(f"    bucket           {task_bucket}, blocked\n")
            lines.append(f"    reason           {task.reason}\n")
            lines.append(f"    waiting on       {task.waiting_on}\n")
        elif task_bucket != "Backlog":
            lines.append(f"    bucket           {task_bucket}\n")
        if task.commit:
            lines.append(f"    commit           {task.commit}\n")
        lines.append(f"    expected output  {task.expected_output}\n")
        if task.description:
            lines.append(f"    description      {task.description}\n")
    return "".join(lines)
