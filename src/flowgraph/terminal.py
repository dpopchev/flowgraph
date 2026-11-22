"""The terminal the output of fgraph is written to: its width and its height, none without one."""

import shutil
import sys
from collections.abc import Callable

# The width in columns of the terminal the output is written to; None when it is no terminal.
Width = Callable[[], int | None]

# The height in lines of the terminal the output is written to; None when it is no terminal.
Height = Callable[[], int | None]


def no_terminal() -> None:
    """The width or the height of an output that is no terminal: none."""
    return None


def terminal_width() -> int | None:
    """Adapter: the columns of the terminal the output of the process is written to.

    None when the output is a pipe or a file.
    """
    return shutil.get_terminal_size().columns if sys.stdout.isatty() else None


def terminal_height() -> int | None:
    """Adapter: the lines of the terminal the output of the process is written to.

    None when the output is a pipe or a file.
    """
    return shutil.get_terminal_size().lines if sys.stdout.isatty() else None
