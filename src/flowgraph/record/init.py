"""The record of a directory made by `fgraph init`: where it goes and what it holds at first.

A record is a directory, and git commits no empty one, so init writes a `config.toml` at the
defaults of every key it names: the commits of the record on, the development off.
"""

from collections.abc import Callable
from pathlib import Path

from flowgraph.development.commit import OpenGit, Said, commit_written
from flowgraph.development.git import GitError
from flowgraph.item.commands import Written
from flowgraph.record.config import Settings, make_config
from flowgraph.record.location import NAMES, IsDir
from flowgraph.record.store import OpenStore

# What the config.toml of a new record holds: the defaults.
INITIAL: Settings = {"git": {"commit": True}, "development": {"enabled": False}}

# Make the directory of the record; what it returns is ignored.
MakeDir = Callable[[Path], object]

# Remove the directory of the record, which holds nothing by then; what it returns is ignored.
RemoveDir = Callable[[Path], object]


class RecordHeldError(ValueError):
    """The directory holds a record already; names it."""


class NoDirectoryError(ValueError):
    """The directory given to make the record in is no directory."""


def place_record(directory: Path, given: Path | None, is_dir: IsDir) -> Path:
    """The path of the record to make: `.fgraph/` in the directory given, else in `directory`.

    Raises NoDirectoryError when the directory given is none, and RecordHeldError naming the
    record when the directory holds `.fgraph/` or `fgraph/` already.
    """
    where = directory if given is None else given
    if given is not None and not is_dir(given):
        raise NoDirectoryError(f"--dir {given} is no directory")
    for name in NAMES:
        if is_dir(where / name):
            raise RecordHeldError(f"{where / name} holds a record already")
    return where / NAMES[0]


def init_record(
    directory: Path,
    given: Path | None,
    is_dir: IsDir,
    make_dir: MakeDir,
    remove_dir: RemoveDir,
    open_store: OpenStore,
    open_git: OpenGit,
) -> Said:
    """Make the record of the directory and say its path; commit it inside a git work tree.

    Raises the refusals of place_record, and GitError when git refuses the commit: the file
    written is taken back and the directory made is removed, so nothing of the record is left.
    """
    record = place_record(directory, given, is_dir)
    make_dir(record)
    store = open_store(record)
    store.save_settings(INITIAL)
    written = Written(f"record: {record}\n", "chore: make the record")
    try:
        return commit_written(written, store, record, open_git, make_config(""))
    except GitError:
        store.restore_files()
        remove_dir(record)
        raise
