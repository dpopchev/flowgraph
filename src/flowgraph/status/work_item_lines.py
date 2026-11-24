"""The lines status writes for one work item with its Tasks being worked, and the words of a wait.

A wait names the ids an item depends on, a block names who it waits on; both are read from the
rows at each listing.
"""

from collections.abc import Sequence

from flowgraph.status.review import counted, ready_for_review
from flowgraph.story import StoryRow
from flowgraph.task import TaskRow
from flowgraph.upkeep import UpkeepRow
from flowgraph.work_item import BLOCKED, IN_PROGRESS, STARTED

# The state of a completed Task, as the record writes it.
COMPLETED = "completed"


def work_item_lines(row: StoryRow | UpkeepRow) -> str:
    """One item of a bucket: its id and title, with its commit or the reason it was removed.

    A started one is marked `?` before its id when it is ready for review; a blocked one `!`,
    ending with what it waits on and why, as a blocked Task. One whose branch is older than its age
    ends its line with `-- its branch is older than 1d`, before a block. Each is listed with
    its Tasks completed of all but the removed, between its id and its title, then
    the agent it is handed to in brackets, if any, and under it each Task of it being worked on a
    line of its own, in the order written. A completed one holds a commit or not: one it holds
    stands before the title, so a line cut to a width keeps it; a reason ends the line.
    """
    if row.state in IN_PROGRESS:
        tasks = counted(row)
        completed = sum(task.state == COMPLETED for task in tasks)
        worked = "".join(_task_line(task) for task in row.tasks)
        handed = f"[{row.agent}]  " if row.agent else ""
        older = (
            f"  -- its branch is older than {row.branch_older_than}"
            if row.branch_older_than
            else ""
        )
        line = f"{row.id}  {completed}/{len(tasks)} T  {handed}{row.title}{older}"
        if row.waiting_on:
            return f"{blocked_line(line, (row.waiting_on, row.block_reason))}\n{worked}"
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
    return f"{waiting_line(f'{row.id}  {row.title}', row.waits_for, next_up=row.next_to_start)}\n"


def waiting_line(line: str, waits_for: Sequence[str], *, next_up: bool = False) -> str:
    """The line of an item of a bucket: marked `~` and ending with the ids it depends on, if any.

    The mark and the words differ from a block, `!` and `waiting on`: a block waits on a person.
    The next to start waits for nothing and is marked `>`.
    """
    if waits_for:
        return f"~ {line}  -- depends on {', '.join(waits_for)}"
    return f"> {line}" if next_up else f"  {line}"


def blocked_line(line: str, block: tuple[str, str]) -> str:
    """The line of an item of a bucket: marked `!` and ending with the block, if any."""
    waiting_on, _ = block
    return f"! {line}  -- {block_text(*block)}" if waiting_on else f"  {line}"


def block_text(waiting_on: str, reason: str) -> str:
    """What a block says: `waiting on <who>`, then `: <reason>` when the reason is known."""
    return f"waiting on {waiting_on}: {reason}" if reason else f"waiting on {waiting_on}"


def _task_line(task: TaskRow) -> str:
    """A Task being worked, under its work item; nothing for one in Backlog, completed or removed.

    A started Task is marked `=>`, a blocked one `!` and ends with what it waits on and why.
    """
    if task.state == STARTED:
        return f"    => {task.id}  {task.title}\n"
    if task.state == BLOCKED:
        return f"    !  {task.id}  {task.title}  -- {block_text(task.waiting_on, task.reason)}\n"
    return ""
