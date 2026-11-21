"""Where the record of a project lives: `.fgraph/` or `fgraph/` in a directory, or a path given."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# The directory of every item inside a record, one file per work item, named by its id.
ITEMS = "items"

# The current time, with its zone.
Now = Callable[[], datetime]

# The names searched for in a directory, in the order they are tried.
NAMES = (".fgraph", "fgraph")

# True when the path names an existing directory; raises nothing.
IsDir = Callable[[Path], bool]


@dataclass(frozen=True)
class Found:
    """The record found by its name in the directory searched."""

    path: Path


@dataclass(frozen=True)
class Given:
    """The record at the path given, taken without a search."""

    path: Path


@dataclass(frozen=True)
class NotFound:
    """No name of the record is a directory in the directory searched."""

    cwd: Path
    tried: tuple[str, ...]


@dataclass(frozen=True)
class GivenMissing:
    """The path given is no directory."""

    path: Path


Location = Found | Given
Missing = NotFound | GivenMissing


def locate(cwd: Path, given: Path | None, is_dir: IsDir) -> Location | Missing:
    """The record of the given path when there is one, else the first of NAMES in cwd.

    A given path is never a reason to search: when it is no directory, that is the answer.
    """
    if given is not None:
        return Given(given) if is_dir(given) else GivenMissing(given)
    for name in NAMES:
        if is_dir(cwd / name):
            return Found(cwd / name)
    return NotFound(cwd, NAMES)
