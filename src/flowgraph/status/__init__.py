"""The status of a record: its items by bucket, the text fgraph writes, the terminal, the watch."""

from flowgraph.status.buckets import APART, BUCKETS
from flowgraph.status.document import StatusFormatError
from flowgraph.status.rows import (
    BACKLOG,
    COMPLETED,
    backlog_as_added,
    rows_by_id,
    rows_under,
)
from flowgraph.status.show import feature_text, show_text
from flowgraph.status.terminal import (
    Height,
    Width,
    no_terminal,
    terminal_height,
    terminal_width,
)
from flowgraph.status.text import cut_lines, status_text
from flowgraph.status.tops import Tops, same_top, tops_asked, tops_of
from flowgraph.status.under import in_show_order
from flowgraph.status.view import find_backlog, status_item, status_output, watch_item
from flowgraph.status.watch import CLEAR, Pace, PaceError, Wait, framed, make_pace, watch
from flowgraph.work_item import STARTED

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
    "StatusFormatError",
    "Tops",
    "Wait",
    "Width",
    "backlog_as_added",
    "cut_lines",
    "feature_text",
    "find_backlog",
    "framed",
    "in_show_order",
    "make_pace",
    "no_terminal",
    "rows_by_id",
    "rows_under",
    "same_top",
    "show_text",
    "status_item",
    "status_output",
    "status_text",
    "terminal_height",
    "terminal_width",
    "tops_asked",
    "tops_of",
    "watch",
    "watch_item",
]
