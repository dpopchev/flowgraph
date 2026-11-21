"""The text fgraph writes for the record: its items by bucket, and one item whole."""

from collections.abc import Collection, Iterable, Sequence

from flowgraph.story import StoryDetail, StoryRow
from flowgraph.upkeep import UpkeepDetail, UpkeepRow

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


def status_text(rows: Iterable[StoryRow | UpkeepRow]) -> str:
    """The items by bucket, in the order of the flow: a heading with its count, then its items.

    A completed item is listed with its commit, a removed one with its reason. Removed stands
    apart from the flow: its heading is listed only when an item is removed.
    """
    listed = list(rows)
    lines: list[str] = []
    for bucket, states in BUCKETS:
        held = [row for row in listed if row.state in states]
        if bucket == APART and not held:
            continue
        lines.append(f"{bucket} ({len(held)})\n")
        lines.extend(_status_line(row) for row in held)
    return "".join(lines)


def _status_line(row: StoryRow | UpkeepRow) -> str:
    """One item of a bucket: its id and title, then its commit or the reason it was removed."""
    if row.commit:
        return f"  {row.id}  {row.title}  {row.commit}\n"
    if row.reason:
        return f"  {row.id}  {row.title}  -- {row.reason}\n"
    return f"  {row.id}  {row.title}\n"


def show_text(detail: StoryDetail | UpkeepDetail) -> str:
    """The work item with its bucket and its criterion, then its Tasks, one fact per line.

    A description, a commit and the reason of a removal are listed only when there is one, the
    bucket of a Task only once it has left Backlog. A blocked Task is listed in InProgress as
    blocked, with its reason and what it waits on.
    """
    bucket = next(name for name, states in BUCKETS if detail.state in states)
    committed = [f"  commit       {detail.commit}\n"] if detail.commit else []
    removed = [f"  reason       {detail.reason}\n"] if detail.reason else []
    described = [f"  description  {detail.description}\n"] if detail.description else []
    lines = [
        f"{detail.id}  {detail.title}\n",
        f"  bucket       {bucket}\n",
        *committed,
        *removed,
        *described,
        f"  given        {detail.given}\n",
        f"  when         {detail.when}\n",
        f"  then         {detail.then}\n",
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
