"""The lines status writes for one work item with its Tasks being worked, and the words of a wait.

A wait names the ids an item depends on, a block names who it waits on; both are read from the
rows at each listing.
"""

from collections.abc import Sequence

from flowgraph.status.review import counted, ready_for_review
from flowgraph.status.rows import BACKLOG
from flowgraph.story import StoryRow
from flowgraph.task import TaskRow
from flowgraph.upkeep import UpkeepRow
from flowgraph.work_item import BLOCKED, IN_PROGRESS, STARTED

# The mark is not special at the start of a line pasted into Markdown nor in a search by a
# regular expression: the set the developer chose on 2026-11-23 (S-0139), whose mark of a line
# that can start he dropped on 2026-11-24 (S-0152).
# A started work item whose Tasks are all completed.
READY_FOR_REVIEW = "@"

# The state of a completed Task, as the record writes it.
COMPLETED = "completed"


def work_item_lines(row: StoryRow | UpkeepRow) -> str:
    """One item of a bucket: its id and title, with its commit or the reason it was removed.

    A started one is marked `@` before its id when it is ready for review; a blocked one `!`,
    with what it waits on and why below its line, as a blocked Task. One whose branch is older than
    its age says `its branch is older than 1d` on a line below its own, before a block. Each is
    listed with its Tasks completed of all but the removed, between its id and its title, then
    the agent it is handed to in brackets, if any, and under it each Task of it being worked on a
    line of its own, in the order written. A completed one holds a commit or not: one it holds
    stands before the title, so a line cut to a width keeps it; a reason is on a line below it.
    One in Backlog is listed with the count of its Tasks in brackets, `[]` for none, between its id
    and its title: the developer's frame of 2026-11-23.
    """
    if row.state in IN_PROGRESS:
        done, total = _progress(row)
        worked = "".join(_task_line(task) for task in row.tasks)
        handed = f"[{row.agent}]  " if row.agent else ""
        older = f"its branch is older than {row.branch_older_than}" if row.branch_older_than else ""
        line = f"{row.id}  {done}/{total} T  {handed}{row.title}"
        if row.waiting_on:
            head = added_below(f"! {line}", older)
            return f"{added_below(head, block_text(row.waiting_on, row.block_reason))}\n{worked}"
        mark = f"{READY_FOR_REVIEW} " if ready_for_review(row) else "  "
        return f"{added_below(f'{mark}{line}', older)}\n{worked}"
    if row.commit:
        return f"  {row.id}  {row.commit}  {row.title}\n"
    why = ", ".join(
        part
        for part in (f"superseded by {row.superseded_by}" if row.superseded_by else "", row.reason)
        if part
    )
    if why:
        return f"{added_below(f'  {row.id}  {row.title}', why)}\n"
    named = (
        f"{row.id}  {_held(row)}  {row.title}" if row.state == BACKLOG else f"{row.id}  {row.title}"
    )
    return f"{waiting_line(named, row.waits_for)}\n"


def completed_line(row: StoryRow | UpkeepRow) -> str:
    """The line of a completed work item under its Feature in progress: its id, Tasks and title.

    It holds no commit, agent or Task line: a completed work item is read, not descended into.
    """
    done, total = _progress(row)
    return f"  {row.id}  {done}/{total} T  {row.title}\n"


def _held(row: StoryRow | UpkeepRow) -> str:
    """The Tasks a work item holds, as `[N T]`, or `[]` when it holds none."""
    return f"[{len(row.tasks)} T]" if row.tasks else "[]"


def _progress(row: StoryRow | UpkeepRow) -> tuple[int, int]:
    """The Tasks completed of those that count in the progress of the row, and how many count."""
    tasks = counted(row)
    return sum(task.state == COMPLETED for task in tasks), len(tasks)


def waiting_line(line: str, waits_for: Sequence[str]) -> str:
    """The line of an item of a bucket: marked `~`, with the ids it depends on below it, if any.

    The mark and the words differ from a block, `!` and `waiting on`: a block waits on a person.
    A line that waits for nothing is not marked, whether or not it can start.
    """
    if waits_for:
        return added_below(f"~ {line}", f"depends on {', '.join(waits_for)}")
    return f"  {line}"


def added_below(line: str, added: str, under: int = 2) -> str:
    """The line alone, or with what it adds on a line of its own right below it.

    What a line adds is put on a line of its own, beginning under the id of who has it: the
    developer's decision of 2026-11-23 on F-0017. `under` is the column of that id.
    """
    return f"{line}\n{' ' * under}{added}" if added else line


def blocked_line(line: str, block: tuple[str, str]) -> str:
    """The line of an item of a bucket: marked `!`, with the block on a line below it, if any."""
    waiting_on, _ = block
    return added_below(f"! {line}", block_text(*block)) if waiting_on else f"  {line}"


def block_text(waiting_on: str, reason: str) -> str:
    """What a block says: `waiting on <who>`, then `: <reason>` when the reason is known."""
    return f"waiting on {waiting_on}: {reason}" if reason else f"waiting on {waiting_on}"


def _task_line(task: TaskRow) -> str:
    """A Task being worked, under its work item; nothing for one in Backlog, completed or removed.

    A started Task is marked `=>`, a blocked one `!`, with what it waits on and why below it.
    """
    if task.state == STARTED:
        return f"    => {task.id}  {task.title}\n"
    if task.state == BLOCKED:
        held = f"    !  {task.id}  {task.title}"
        return f"{added_below(held, block_text(task.waiting_on, task.reason), under=7)}\n"
    return ""
