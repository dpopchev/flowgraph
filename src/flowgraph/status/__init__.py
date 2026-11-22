"""The status of a record: its items by bucket, the text fgraph writes, the terminal, the watch."""

from flowgraph.status.terminal import (
    Height,
    Width,
    no_terminal,
    terminal_height,
    terminal_width,
)
from flowgraph.status.text import (
    APART,
    BUCKETS,
    cut_lines,
    feature_text,
    show_text,
    status_text,
)
from flowgraph.status.view import (
    BACKLOG,
    COMPLETED,
    STARTED,
    backlog_as_added,
    find_backlog,
    rows_by_id,
    rows_under,
    status_item,
)
from flowgraph.status.watch import CLEAR, Pace, PaceError, Wait, framed, make_pace, watch

__all__ = [
    "APART",
    "BACKLOG",
    "BUCKETS",
    "CLEAR",
    "COMPLETED",
    "STARTED",
    "Height",
    "Pace",
    "PaceError",
    "Wait",
    "Width",
    "backlog_as_added",
    "cut_lines",
    "feature_text",
    "find_backlog",
    "framed",
    "make_pace",
    "no_terminal",
    "rows_by_id",
    "rows_under",
    "show_text",
    "status_item",
    "status_text",
    "terminal_height",
    "terminal_width",
    "watch",
]
