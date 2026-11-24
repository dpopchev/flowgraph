"""The `fgraph` command line: it locates the record and runs the command on it.

Without a command it shows the help menu and names the record. The command the arguments name
is run on the record by flowgraph.parser.command.
"""

import argparse
import sys
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Never, assert_never

from flowgraph.development import RunGate, run_gate
from flowgraph.development.commit import OpenGit, open_git
from flowgraph.development.scope import scope_in, within, worktree_of_item
from flowgraph.development.worktrees import across_worktrees, held_elsewhere, record_of_main
from flowgraph.item.commands import status_item
from flowgraph.parser import REFUSED, TOP, build_command_line, help_asked
from flowgraph.parser.command import command_said
from flowgraph.parser.ids import ids_read
from flowgraph.record import (
    Config,
    Found,
    Given,
    GivenMissing,
    IsDir,
    LoadConfig,
    NotFound,
    Now,
    locate,
    make_config,
    read_config,
)
from flowgraph.record.init import MakeDir, init_record
from flowgraph.record.store import OpenStore, Store, open_files
from flowgraph.relation.read import check_relations
from flowgraph.status.next import start_limit
from flowgraph.status.terminal import Height, Width, no_terminal, terminal_height, terminal_width
from flowgraph.status.watch import Wait, framed, make_pace, watch

__all__ = ["Store", "open_files", "open_git", "read_config", "run", "run_gate"]

# Write text to a stream; what it returns is ignored, so a stream's write and a list's append fit.
Write = Callable[[str], object]

# The commands that list the record of main when run in the worktree of a work item (S-0141).
LISTS_MAIN = ("status", "watch")


def _no_wait(seconds: float) -> None:
    """The wait of a run given none: the next frame of watch follows at once."""


def _no_config(record: Path) -> Config:
    """The configuration of a run given none to read: the defaults, whatever the record holds."""
    return make_config("")


def _no_gate(command: str, directory: Path) -> Never:
    """The gate of a run given none to run it: a contract, such a run lands under no gate."""
    raise AssertionError(f"run() was given no run_gate to run {command!r} in {directory}")


def _no_check(command: str, directory: Path) -> int:
    """The check runner of a run given none: it runs nothing and says every check passed."""
    return 0


def _no_dir(path: Path) -> Never:
    """The make_dir of a run given none: a contract, such a run makes no record."""
    raise AssertionError(f"run() was given no make_dir to make {path}")


def _read_record(command: str | None, located: Path, open_git: OpenGit) -> Path:
    """The record a command reads: that of main for a LISTS_MAIN command in a work item's worktree.

    The rule is keyed on the work tree that keeps the record, as scope_in is, not on the directory
    fgraph runs in. Every other command, and a record with no record of main, reads the located one.
    """
    if command not in LISTS_MAIN:
        return located
    return record_of_main(located, open_git) or located


def _watch(
    args: argparse.Namespace,
    store: Store,
    write: Write,
    wait: Wait,
    width: Width,
    height: Height,
    config: Config,
) -> None:
    """Write the frames of watch on the record: each what status writes then, read anew.

    A frame is cut to the width and the height the terminal has then and replaces the one
    before it; without a width it is whole and follows it. The configuration sets how many
    lines a frame marks as able to start. Raises PaceError when the seconds or the count asked
    for are no positive number; no frame is written then.
    """
    pace = make_pace(args.seconds, args.count)
    top = None if args.all else TOP
    limit = start_limit(config.development)

    def read_frame() -> str:
        return framed(status_item(store, top, limit), width(), height())

    watch(read_frame, write, wait, pace)


def run(
    argv: Sequence[str],
    cwd: Path,
    is_dir: IsDir,
    write: Write,
    write_error: Write,
    *,
    open_store: OpenStore,
    open_git: OpenGit,
    now: Now,
    width: Width = no_terminal,
    height: Height = no_terminal,
    wait: Wait = _no_wait,
    load_config: LoadConfig = _no_config,
    run_gate: RunGate = _no_gate,
    run_check: RunGate = _no_check,
    make_dir: MakeDir = _no_dir,
) -> int:
    """Read the arguments, locate the record in cwd, run the command and return the exit status.

    The help option needs no record, after a command as alone: it prints the help of the command
    the arguments name; so does init, which makes the record through make_dir and fails with 2
    where one is held. Every other call fails with 2 when there is no record. A write finds the
    git work tree of the record through open_git and is committed there. Run in the worktree of
    a work item, status and watch read the record of main, as a run on main does; every other
    command reads the record it is run on. The lines of status are
    cut to the width of the terminal; without one, as by default, they are whole. Watch writes
    its frames as it goes, each cut to the height of the terminal too, and waits between two by
    wait, which by default returns at once; it
    exits with 0 once its count is written or Ctrl-C ends it. The configuration of the record is
    read through load_config before any command runs, the defaults by default; one that is
    refused fails with 2, whatever the command, and so does a record whose relation names nothing
    or closes a cycle, which is checked as the worktrees compose it, before any command runs. A
    landing runs the gate of the configuration through run_gate, which a run that lands under a
    gate is given: the default runs none. The complete of a Task that holds a check runs it
    through run_check, which a run that must refuse a failing one is given: the default runs
    none, and every check then passes.
    """
    command_line = build_command_line()
    parser = command_line.parser
    asked = help_asked(argv, command_line)
    if asked is not None:
        write(asked)
        return 0
    args = ids_read(parser.parse_args(argv))
    if args.command == "init":
        try:
            made = init_record(cwd, args.dir, is_dir, make_dir, open_store, open_git)
        except REFUSED as error:
            write_error(f"{parser.format_usage()}fgraph: error: {error}\n")
            return 2
        write(made.out)
        return 0
    match locate(cwd, args.dir, is_dir):
        case Found(located) | Given(located):
            path = _read_record(args.command, located, open_git)
            store = within(
                across_worktrees(open_store(path), path, open_git, open_store),
                partial(scope_in, path, open_git),
                partial(worktree_of_item, path, open_git),
            )
            try:
                config = load_config(path)
                check_relations(path, store, partial(held_elsewhere, path, open_git, open_store))
                if args.command == "watch":
                    _watch(args, store, write, wait, width, height, config)
                    return 0
                said = command_said(
                    args, store, now, path, open_git, width, config, run_gate, cwd, run_check
                )
            except REFUSED as error:
                write_error(f"{parser.format_usage()}fgraph: error: {error}\n")
                return 2
            if said is None:
                write(parser.format_help())
                write(f"record: {path}\n")
                return 0
            write(said.out)
            if said.warning:
                write_error(said.warning)
            return 0
        case NotFound(searched, tried):
            names = " or ".join(f"{name}/" for name in tried)
            write_error(f"{parser.format_usage()}fgraph: error: no {names} in {searched}")
            write_error(" -- run fgraph init, or pass --dir PATH\n")
            return 2
        case GivenMissing(path):
            write_error(f"{parser.format_usage()}fgraph: error: --dir {path} is no directory\n")
            return 2
        case _ as unreachable:
            assert_never(unreachable)


def main() -> None:
    """Run the command in the working directory of the process, on its arguments and streams.

    Each write to stdout is flushed, so a frame of watch reaches a pipe as it is written.
    """
    sys.exit(
        run(
            sys.argv[1:],
            Path.cwd(),
            Path.is_dir,
            partial(print, end="", flush=True),
            sys.stderr.write,
            open_store=open_files,
            open_git=open_git,
            now=lambda: datetime.now(UTC),
            width=terminal_width,
            height=terminal_height,
            wait=time.sleep,
            load_config=read_config,
            run_gate=run_gate,
            run_check=run_gate,
            make_dir=Path.mkdir,
        )
    )


if __name__ == "__main__":
    main()
