"""The lock of a record: a write of the record is made alone (B-0035).

A write takes the lock of the directory of its record before it reads and holds it through its
commit, so two fgraph run at one time never read the same ids or write the same file. The lock
is flock of fcntl on the directory itself, so no file is added and git sees nothing. It is that
of one copy of the record, so the worktree of a work item has its own. Linux and macOS alone.
"""

import fcntl
import os
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path


class LockedError(Exception):
    """A record another fgraph is writing: its lock was not given within the wait."""


# Wait that many seconds; what it returns is ignored, so time.sleep fits.
Wait = Callable[[float], object]

# Hold the lock of the record in that directory; raises LockedError when it is not given.
LockRecord = Callable[[Path], AbstractContextManager[None]]

# How many times a lock is tried, and the seconds waited between two tries: ten seconds in all.
TRIES = 100
PAUSE = 0.1

BEING_WRITTEN = "{record} is being written by another fgraph: run the command again"


@contextmanager
def lock_files(
    record: Path, wait: Wait, tries: int = TRIES, pause: float = PAUSE
) -> Iterator[None]:
    """Adapter: hold the flock of the directory of the record through the block.

    The lock is tried that many times, wait(pause) between two; given none it raises
    LockedError naming the record as given. Closing the descriptor gives the lock back, also
    when the body raises or the lock was refused.
    """
    descriptor = os.open(record, os.O_RDONLY)
    try:
        for attempt in range(tries):
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if attempt < tries - 1:
                    wait(pause)
        else:
            raise LockedError(BEING_WRITTEN.format(record=record))
        yield
    finally:
        os.close(descriptor)
