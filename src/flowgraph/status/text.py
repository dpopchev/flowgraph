"""The text fgraph writes for the record: its items by bucket.

The text of one item whole is in flowgraph.status.show.
"""

from collections.abc import Collection, Iterable, Sequence
from typing import assert_never

from flowgraph.feature import FeatureRow
from flowgraph.status.next import start_now_ids
from flowgraph.status.review import ready_for_review, review_ids
from flowgraph.story import StoryRow
from flowgraph.task import TaskRow
from flowgraph.upkeep import UpkeepRow
from flowgraph.work_item import IN_PROGRESS, STARTED, WorkItemRow

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
    holds; its count stays that of all of them. The next to start is marked `>`; one the top
    leaves out is listed after the top, apart from the count of those more.
    """
    listed = list(rows)
    lines: list[str] = []
    for bucket, states in BUCKETS:
        in_bucket = [row for row in listed if is_listed_in(row, bucket, states)]
        held = [_item_lines(row) for row in in_bucket]
        if bucket == APART and not held:
            continue
        pinned = [
            at for at, row in enumerate(in_bucket) if start_now_ids([row]) or review_ids([row])
        ]
        lines.append(f"{bucket} ({len(held)})\n")
        lines.extend(_top_of(held, top, pinned))
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


def is_listed_in(row: WorkItemRow | FeatureRow, bucket: str, states: Collection[str]) -> bool:
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
    further in. A blocked one is marked `!` before its id and ends with what it waits on and why. So
    is one whose work item is blocked or holds a blocked Task, with what the first such says, as
    the line of it does: read from the rows at each listing, and kept nowhere. The block of the
    Feature itself comes first, then that of a work item, then that of a Task. A removed one is
    listed as a removed work
    item is, its reason ending the line, without the progress: its work items have no line.
    """
    if feature.reason:
        return f"  {feature.id}  {feature.title}  -- {feature.reason}\n"
    progress = f"{feature.completed}/{feature.held} W"
    commit = f"{feature.commit}  " if feature.commit else ""
    marked = (row for row in feature.work_items if row.next_to_start)
    started = (
        line for row in (*feature.started, *marked) for line in _status_line(row).splitlines()
    )
    under = "".join(f"  {line}\n" for line in started)
    line = f"{feature.id}  {progress}  {commit}{feature.title}"
    own = (feature.waiting_on, feature.block_reason)
    block = own if feature.waiting_on else _waited_on(feature.started)
    head = (
        _marked(line, block)
        if block[0]
        else _waiting(line, feature.waits_for, next_up=feature.next_to_start)
    )
    return f"{head}\n{under}"


def _waiting(line: str, waits_for: Sequence[str], *, next_up: bool = False) -> str:
    """The line of an item of a bucket: marked `~` and ending with the ids it depends on, if any.

    The mark and the words differ from a block, `!` and `waiting on`: a block waits on a person.
    The next to start waits for nothing and is marked `>`.
    """
    if waits_for:
        return f"~ {line}  -- depends on {', '.join(waits_for)}"
    return f"> {line}" if next_up else f"  {line}"


def _marked(line: str, block: tuple[str, str]) -> str:
    """The line of an item of a bucket: marked `!` and ending with the block, if any."""
    waiting_on, _ = block
    return f"! {line}  -- {_block_text(*block)}" if waiting_on else f"  {line}"


def _block_text(waiting_on: str, reason: str) -> str:
    """What a block says: `waiting on <who>`, then `: <reason>` when the reason is known."""
    return f"waiting on {waiting_on}: {reason}" if reason else f"waiting on {waiting_on}"


def _waited_on(rows: Iterable[StoryRow | UpkeepRow]) -> tuple[str, str]:
    """What the first block of the work items waits on and why; empty when none is blocked.

    Per work item in the order given, its own block comes first, then that of its first blocked
    Task.
    """
    blocked = (
        block
        for row in rows
        for block in (
            (row.waiting_on, row.block_reason),
            *((task.waiting_on, task.reason) for task in row.tasks if task.state == BLOCKED),
        )
        if block[0]
    )
    return next(blocked, ("", ""))


def _top_of(items: Sequence[str], top: int | None, pinned: Collection[int] = ()) -> list[str]:
    """The first items up to the top, then how many more there are; every item without a top.

    An item is counted once, whatever the lines it is written in: a work item with its Tasks
    being worked, a Feature with its started work items. Each pinned item, by its place, is
    listed after the top in its order when the top leaves it out, and is not one of those more.
    """
    if top is None or len(items) <= top:
        return list(items)
    shown = list(items[:top])
    left_out = [at for at in sorted(pinned) if at >= top]
    shown.extend(items[at] for at in left_out)
    more = len(items) - top - len(left_out)
    return [*shown, f"  ... {more} more\n"] if more else shown


def _status_line(row: StoryRow | UpkeepRow) -> str:
    """One item of a bucket: its id and title, with its commit or the reason it was removed.

    A started one is marked `?` before its id when it is ready for review; a blocked one `!`,
    ending with what it waits on and why, as a blocked Task. Each is listed with
    its Tasks completed of all, between its id and its title, then
    the agent it is handed to in brackets, if any, and under it each Task of it being worked on a
    line of its own, in the order written. A completed one holds a commit or not: one it holds
    stands before the title, so a line cut to a width keeps it; a reason ends the line.
    """
    if row.state in IN_PROGRESS:
        completed = sum(task.state == COMPLETED for task in row.tasks)
        worked = "".join(_task_line(task) for task in row.tasks)
        handed = f"[{row.agent}]  " if row.agent else ""
        line = f"{row.id}  {completed}/{len(row.tasks)} T  {handed}{row.title}"
        if row.waiting_on:
            return f"{_marked(line, (row.waiting_on, row.block_reason))}\n{worked}"
        mark = "? " if ready_for_review(row) else "  "
        return f"{mark}{line}\n{worked}"
    if row.commit:
        return f"  {row.id}  {row.commit}  {row.title}\n"
    why = ", ".join(
        part
        for part in (f"superseded by {row.superseded_by}" if row.superseded_by else "", row.reason)
        if part
    )
    if why:
        return f"  {row.id}  {row.title}  -- {why}\n"
    return f"{_waiting(f'{row.id}  {row.title}', row.waits_for, next_up=row.next_to_start)}\n"


def _task_line(task: TaskRow) -> str:
    """A Task being worked, under its work item; nothing for one in Backlog or completed.

    A started Task is marked `=>`, a blocked one `!` and ends with what it waits on and why.
    """
    if task.state == STARTED:
        return f"    => {task.id}  {task.title}\n"
    if task.state == BLOCKED:
        return f"    !  {task.id}  {task.title}  -- {_block_text(task.waiting_on, task.reason)}\n"
    return ""
