"""The frames of `fgraph watch`: a text read anew and written every interval, until it ends."""

import math
from collections.abc import Callable
from dataclasses import dataclass
from itertools import count

from flowgraph.status.text import cut_lines

# What a frame on a terminal opens with: the cursor put home and the screen cleared.
CLEAR = "\x1b[H\x1b[2J"

# The text of the frame of now, read anew by every call.
ReadFrame = Callable[[], str]

# Write a frame to the output; what it returns is ignored.
WriteFrame = Callable[[str], object]

# Wait that many seconds before the next frame.
Wait = Callable[[float], object]


class PaceError(ValueError):
    """Seconds between two frames, or a count of frames, that is no positive number."""


@dataclass(frozen=True)
class Pace:
    """How a watch goes on: the seconds between two frames, and the frames it ends after.

    Without a count it ends only when it is interrupted.
    """

    seconds: float
    count: int | None


def make_pace(seconds: float, count: int | None) -> Pace:
    """The pace of those seconds and that count.

    Raises PaceError when the seconds are no positive number, an endless wait among them, or
    the count is below one.
    """
    if not (math.isfinite(seconds) and seconds > 0):
        raise PaceError(f"-n {seconds:g} is no positive number of seconds")
    if count is not None and count < 1:
        raise PaceError(f"--count {count} is no positive number of frames")
    return Pace(seconds, count)


def framed(text: str, width: int | None, height: int | None = None) -> str:
    """The text as a frame on a terminal that wide: it replaces the frame before, each line cut.

    On a terminal that high it keeps one line below it free, so the frame does not scroll: a
    text taller than that keeps its first lines and ends with one naming how many it left out.
    Without a width the output is no terminal: the text is whole, and a frame follows the one
    before it; without a height no line is left out.
    """
    if width is None:
        return text
    return f"{CLEAR}{cut_lines(_cut_height(text, height), width)}"


def _cut_height(text: str, height: int | None) -> str:
    """The text kept to one line under that height, its last line naming the lines left out."""
    lines = text.splitlines(keepends=True)
    if height is None or len(lines) < height:
        return text
    kept = max(height - 2, 0)
    return "".join(lines[:kept]) + f"... {len(lines) - kept} more lines\n"


def watch(read_frame: ReadFrame, write: WriteFrame, wait: Wait, pace: Pace) -> None:
    """Write a frame, wait the seconds of the pace and write the next, until the pace ends it.

    No wait follows the last frame. An interrupt from the keyboard ends it as its count does,
    wherever it falls: Ctrl-C is how a watch without a count is left, so it is no failure.
    """
    try:
        for written in count(1):
            write(read_frame())
            if written == pace.count:
                return
            wait(pace.seconds)
    except KeyboardInterrupt:
        return
