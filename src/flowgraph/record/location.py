"""Where the record lives: the path given, the folder a key names, `.fgraph/` or `fgraph/`."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import assert_never

# The directory of every item inside a record, one file per work item, named by its id.
ITEMS = "items"

# The current time, with its zone.
Now = Callable[[], datetime]

# The names searched for in a directory, in the order they are tried.
NAMES = (".fgraph", "fgraph")

# True when the path names an existing directory; raises nothing.
IsDir = Callable[[Path], bool]

# The key of the git configuration of a clone that names the folder of its record, relative to
# the root of the repository; the developer sets it with git config, fgraph only reads it.
KEY = "fgraph.record"

# The folder the git configuration of the clone the directory is inside names for the record, as
# a path under the root of its work tree; None outside a git work tree and when the key is not
# set; raises nothing.
FindNamed = Callable[[Path], Path | None]


def no_name(directory: Path) -> None:
    """Name nothing: the find_named of a run given none."""
    return None


@dataclass(frozen=True)
class Found:
    """The record found by the key or by its name in the directory searched."""

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


@dataclass(frozen=True)
class NamedMissing:
    """The folder the key names is no directory."""

    path: Path


Location = Found | Given
Missing = NotFound | GivenMissing | NamedMissing


def locate(
    cwd: Path, given: Path | None, is_dir: IsDir, find_named: FindNamed = no_name
) -> Location | Missing:
    """The record of the given path, else the folder the key names, else the first of NAMES in cwd.

    A given path is never a reason to search: when it is no directory, that is the answer. A
    folder the key names that is no directory is the answer too, with no fall back to NAMES.
    """
    if given is not None:
        return Given(given) if is_dir(given) else GivenMissing(given)
    named = find_named(cwd)
    if named is not None:
        return Found(named) if is_dir(named) else NamedMissing(named)
    for name in NAMES:
        if is_dir(cwd / name):
            return Found(cwd / name)
    return NotFound(cwd, NAMES)


def why_missing(missing: Missing) -> str:
    """The words after `fgraph: error:` for a record that was not found."""
    match missing:
        case NotFound(cwd, tried):
            names = " or ".join(f"{name}/" for name in tried)
            return f"no {names} in {cwd} -- run fgraph init, or pass --dir PATH"
        case GivenMissing(path):
            return f"--dir {path} is no directory"
        case NamedMissing(path):
            return (
                f"git config {KEY} names {path}, which is no directory"
                f" -- run fgraph init, or name another with git config {KEY} PATH"
            )
        case _ as unreachable:
            assert_never(unreachable)
