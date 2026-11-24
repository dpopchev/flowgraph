"""The lines status writes for one Feature, with the work items listed under it.

A block of the Feature, of a work item or of a Task comes first, as the line of it shows.
"""

from collections.abc import Iterable

from flowgraph.feature import FeatureRow
from flowgraph.status.work_item_lines import blocked_line, waiting_line, work_item_lines
from flowgraph.story import StoryRow
from flowgraph.upkeep import UpkeepRow
from flowgraph.work_item import BLOCKED


def feature_lines(feature: FeatureRow) -> str:
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
        line for row in (*feature.started, *marked) for line in work_item_lines(row).splitlines()
    )
    under = "".join(f"  {line}\n" for line in started)
    line = f"{feature.id}  {progress}  {commit}{feature.title}"
    own = (feature.waiting_on, feature.block_reason)
    block = own if feature.waiting_on else _waited_on(feature.started)
    head = (
        blocked_line(line, block)
        if block[0]
        else waiting_line(line, feature.waits_for, next_up=feature.next_to_start)
    )
    return f"{head}\n{under}"


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
