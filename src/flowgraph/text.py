"""The text fgraph writes for the record: its items by bucket, and one item whole."""

from collections.abc import Collection, Iterable, Sequence

from flowgraph.story import StoryDetail, StoryRow
from flowgraph.upkeep import UpkeepDetail, UpkeepRow

# The buckets of the flow in their order, each with the states of an item shown in it.
BUCKETS: Sequence[tuple[str, Collection[str]]] = (
    ("Backlog", frozenset({"backlog"})),
    ("InProgress", frozenset({"started"})),
    ("Completed", frozenset({"completed"})),
)


def status_text(rows: Iterable[StoryRow | UpkeepRow]) -> str:
    """The items by bucket, in the order of the flow: a heading with its count, then its items.

    A completed item is listed with its commit.
    """
    listed = list(rows)
    lines: list[str] = []
    for bucket, states in BUCKETS:
        held = [row for row in listed if row.state in states]
        lines.append(f"{bucket} ({len(held)})\n")
        lines.extend(
            f"  {row.id}  {row.title}  {row.commit}\n"
            if row.commit
            else f"  {row.id}  {row.title}\n"
            for row in held
        )
    return "".join(lines)


def show_text(detail: StoryDetail | UpkeepDetail) -> str:
    """The work item with its bucket and its criterion, then its Tasks, one fact per line.

    A description and a commit are listed only when there is one, the bucket of a Task only once
    it has left Backlog.
    """
    bucket = next(name for name, states in BUCKETS if detail.state in states)
    committed = [f"  commit       {detail.commit}\n"] if detail.commit else []
    described = [f"  description  {detail.description}\n"] if detail.description else []
    lines = [
        f"{detail.id}  {detail.title}\n",
        f"  bucket       {bucket}\n",
        *committed,
        *described,
        f"  given        {detail.given}\n",
        f"  when         {detail.when}\n",
        f"  then         {detail.then}\n",
        f"Tasks ({len(detail.tasks)})\n",
    ]
    for task in detail.tasks:
        lines.append(f"  {task.id}  {task.title}\n")
        task_bucket = next(name for name, states in BUCKETS if task.state in states)
        if task_bucket != "Backlog":
            lines.append(f"    bucket           {task_bucket}\n")
        if task.commit:
            lines.append(f"    commit           {task.commit}\n")
        lines.append(f"    expected output  {task.expected_output}\n")
        if task.description:
            lines.append(f"    description      {task.description}\n")
    return "".join(lines)
