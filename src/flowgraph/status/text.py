"""The text fgraph writes for the record: its items by bucket.

The text of one item whole is in flowgraph.status.show.
"""

from collections.abc import Collection, Iterable, Sequence
from typing import assert_never

from flowgraph.feature import FeatureRow
from flowgraph.status.buckets import APART, BACKLOG_BUCKET, BUCKETS, is_listed_in
from flowgraph.status.feature_lines import feature_lines
from flowgraph.status.next import start_now_ids
from flowgraph.status.review import review_ids
from flowgraph.status.tops import WHOLE, Tops, top_of
from flowgraph.status.work_item_lines import work_item_lines
from flowgraph.work_item import WorkItemRow

# What ends a line cut to the width of the terminal.
CUT = "..."


def status_text(
    rows: Iterable[WorkItemRow | FeatureRow],
    tops: Tops = WHOLE,
    buckets: Collection[str] | None = None,
) -> str:
    """The items by bucket, in the order of the flow: a heading with its count, then its items.

    A completed item is listed with its commit when it holds one, a removed one with its reason.
    Removed stands apart from the flow: its heading is listed only when an item is removed. A
    Feature is one item of its bucket, listed among the work items in the order given. Under a
    top, each heading having its own, it lists that many of its items, the first ones given,
    then how many more it holds; its count stays that of all of them. A line marked `=` as able
    to start that the top leaves out is listed after it in InProgress; in the Backlog it is counted
    in the more-line, `... N more, M can start`, and not listed. Only the buckets named in
    `buckets` are listed, heading and items; none lists every bucket.
    """
    listed = list(rows)
    lines: list[str] = []
    for bucket, states in BUCKETS:
        if buckets is not None and bucket not in buckets:
            continue
        in_bucket = [row for row in listed if is_listed_in(row, bucket, states)]
        held = [_item_lines(row) for row in in_bucket]
        if bucket == APART and not held:
            continue
        pinned = [
            at for at, row in enumerate(in_bucket) if start_now_ids([row]) or review_ids([row])
        ]
        lines.append(f"{bucket} ({len(held)})\n")
        top = top_of(tops, bucket)
        if bucket == BACKLOG_BUCKET:
            lines.extend(_top_of_backlog(held, top, pinned))
        else:
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


def _item_lines(row: WorkItemRow | FeatureRow) -> str:
    """One item of a bucket in the lines it is written in: a work item, or a Feature."""
    match row:
        case FeatureRow():
            return feature_lines(row)
        case WorkItemRow():
            return work_item_lines(row)
        case _ as unreachable:
            assert_never(unreachable)


def _top_of_backlog(items: Sequence[str], top: int | None, can_start: Collection[int]) -> list[str]:
    """The first items up to the top, then how many more there are and how many can start.

    The places in can_start at or beyond the top are counted in the more-line, never listed;
    every item without a top or when the top leaves none out.
    """
    if top is None or len(items) <= top:
        return list(items)
    able = sum(at >= top for at in can_start)
    return [*items[:top], f"  ... {len(items) - top} more, {able} can start\n"]


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
