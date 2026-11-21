"""The text fgraph writes for the record: its items by bucket, and one item whole."""

from collections.abc import Collection, Iterable, Sequence

from flowgraph.feature import FeatureDetail, FeatureRow
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


def status_text(
    rows: Iterable[StoryRow | UpkeepRow],
    features: Iterable[FeatureRow] = (),
    top: int | None = None,
) -> str:
    """The items by bucket, in the order of the flow: a heading with its count, then its items.

    A completed item is listed with its commit, a removed one with its reason. Removed stands
    apart from the flow: its heading is listed only when an item is removed. The Features come
    first, under a heading of their own, each with its derived bucket; that heading is listed
    only when there is a Feature. Under a top a heading lists that many of its items, the first
    ones given, then how many more it holds; its count stays that of all of them.
    """
    listed = list(rows)
    grouping = [f"  {feature.id}  {feature.title}  {feature.bucket}\n" for feature in features]
    lines = [f"Features ({len(grouping)})\n", *_top_of(grouping, top)] if grouping else []
    for bucket, states in BUCKETS:
        held = [_status_line(row) for row in listed if row.state in states]
        if bucket == APART and not held:
            continue
        lines.append(f"{bucket} ({len(held)})\n")
        lines.extend(_top_of(held, top))
    return "".join(lines)


def _top_of(lines: Sequence[str], top: int | None) -> list[str]:
    """The first lines up to the top, then how many more there are; every line without a top."""
    if top is None or len(lines) <= top:
        return list(lines)
    return [*lines[:top], f"  ... {len(lines) - top} more\n"]


def _status_line(row: StoryRow | UpkeepRow) -> str:
    """One item of a bucket: its id and title, then its commit or the reason it was removed."""
    if row.commit:
        return f"  {row.id}  {row.title}  {row.commit}\n"
    if row.reason:
        return f"  {row.id}  {row.title}  -- {row.reason}\n"
    return f"  {row.id}  {row.title}\n"


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
