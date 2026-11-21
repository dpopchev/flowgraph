"""The `fgraph` command line: it locates the record and runs the command on it.

Without a command it shows the help menu and names the record.
"""

import argparse
import shutil
import sys
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import assert_never

from flowgraph.branch import GitError, SlugError
from flowgraph.commit import OpenGit, Said, commit_written, open_git
from flowgraph.criterion import (
    CommitError,
    Criterion,
    CriterionError,
    DecisionError,
    EmptyPartError,
    make_defect,
    make_hypothesis,
    make_scenario,
)
from flowgraph.feature import FeatureNotFoundError, NoCriterionError
from flowgraph.feature_item import (
    add_feature_item,
    is_feature_id,
    parent_named,
    show_feature_item,
)
from flowgraph.item import (
    ItemIdError,
    Written,
    add_item,
    amend_item,
    block_item,
    complete_item,
    kind_named,
    remove_item,
    reorder_item,
    show_item,
    start_item,
    status_item,
    unblock_item,
    write_task,
)
from flowgraph.land import LandError, land_item
from flowgraph.parent import FeatureIdError
from flowgraph.parser import TOP, build_command_line, help_asked
from flowgraph.queue import NotInBacklogError, SameItemError
from flowgraph.record import Found, Given, GivenMissing, IsDir, NotFound, Now, locate
from flowgraph.scope import (
    NotOnMainError,
    OutOfScopeError,
    check_start_on_main,
    scope_in,
    within,
    worktree_of_item,
)
from flowgraph.store import OpenStore, Store, open_files
from flowgraph.task import (
    BlockedError,
    CompletedAlreadyError,
    ItemInBacklogError,
    NoTaskError,
    NotBlockedError,
    NotStartedError,
    OpenTaskError,
    StartedAlreadyError,
    TaskIdError,
    TaskInProgressError,
    TaskNotFoundError,
)
from flowgraph.text import cut_lines
from flowgraph.watch import PaceError, Wait, framed, make_pace, watch
from flowgraph.work_item import (
    Amendment,
    NoPartError,
    NoSuchPartError,
    RemovedAlreadyError,
    WorkItemIdError,
    WorkItemNotFoundError,
)
from flowgraph.worktrees import across_worktrees

__all__ = ["Store", "open_files", "open_git", "run"]

# Write text to a stream; what it returns is ignored, so a stream's write and a list's append fit.
Write = Callable[[str], object]

# The width in columns of the terminal the output is written to; None when it is no terminal.
Width = Callable[[], int | None]

# The refusals of a command, each written as a usage error; a git step refused among them.
REFUSED = (
    ItemIdError,
    WorkItemIdError,
    FeatureIdError,
    FeatureNotFoundError,
    NoCriterionError,
    SlugError,
    GitError,
    LandError,
    NotOnMainError,
    OutOfScopeError,
    CommitError,
    EmptyPartError,
    CriterionError,
    DecisionError,
    NoPartError,
    NoSuchPartError,
    RemovedAlreadyError,
    WorkItemNotFoundError,
    TaskIdError,
    TaskNotFoundError,
    NoTaskError,
    NotStartedError,
    StartedAlreadyError,
    BlockedError,
    NotBlockedError,
    TaskInProgressError,
    ItemInBacklogError,
    OpenTaskError,
    CompletedAlreadyError,
    NotInBacklogError,
    SameItemError,
    PaceError,
)


def _criterion(args: argparse.Namespace) -> Criterion:
    """The criterion the arguments of an add state, in the form the kind added takes.

    Raises EmptyPartError naming the first part that is blank.
    """
    match args.kind:
        case "bug":
            return make_defect(args.observed, args.expected)
        case "spike":
            return make_hypothesis(args.hypothesis)
        case _:
            return make_scenario(args.given, args.when, args.then)


def _written(args: argparse.Namespace, store: Store, now: Now) -> Written | None:
    """Make the write the arguments name on the store; None when they name a view or no command.

    Raises the refusal of the write; nothing is saved then.
    """
    match args.command:
        case "add" if args.kind == "task":
            return write_task(args.parent, args.title, args.output, args.description, store, now)
        case "add" if args.kind == "feature":
            return add_feature_item(args.title, args.criterion, args.description, store, now)
        case "add":
            kind = kind_named(args.kind)
            under = parent_named(args.parent, store)
            criterion = _criterion(args)
            return add_item(kind, args.title, criterion, args.description, store, now, under)
        case "amend":
            parts = Amendment(
                args.title,
                args.description,
                args.given,
                args.when,
                args.then,
                args.observed,
                args.expected,
                args.hypothesis,
            )
            return amend_item(args.id, parts, store)
        case "complete":
            return complete_item(args.id, args.commit, store, now, args.decision)
        case "start":
            return start_item(args.id, args.slug, store, now)
        case "block":
            return block_item(args.id, args.reason, args.waiting_on, store, now)
        case "unblock":
            return unblock_item(args.id, store)
        case "remove":
            return remove_item(args.id, args.reason, store, now)
        case "reorder":
            return reorder_item(args.id, args.before, store)
        case _:
            return None


def _no_terminal() -> None:
    """The width of an output that is no terminal: none."""
    return None


def _no_wait(seconds: float) -> None:
    """The wait of a run given none: the next frame of watch follows at once."""


def terminal_width() -> int | None:
    """Adapter: the columns of the terminal the output of the process is written to.

    None when the output is a pipe or a file.
    """
    return shutil.get_terminal_size().columns if sys.stdout.isatty() else None


def _said(
    args: argparse.Namespace,
    store: Store,
    now: Now,
    record: Path,
    open_git: OpenGit,
    width: Width,
) -> Said | None:
    """Run the command the arguments name on the record; None when they name none.

    A write is committed once it is made. The lines of status are cut to the width, when there
    is one. Raises the refusal of the command, a git step refused among them.
    """
    if args.command == "start":
        check_start_on_main(args.id, record, open_git)
    written = _written(args, store, now)
    if written is not None:
        return commit_written(written, store, record, open_git)
    match args.command:
        case "land":
            return land_item(args.id, args.message, store, now, record, open_git, args.decision)
        case "show" if is_feature_id(args.id):
            return Said(show_feature_item(args.id, store))
        case "show":
            return Said(show_item(args.id, store))
        case "status":
            return Said(cut_lines(status_item(store, None if args.all else TOP), width()))
        case _:
            return None


def _watch(args: argparse.Namespace, store: Store, write: Write, wait: Wait, width: Width) -> None:
    """Write the frames of watch on the record: each what status writes then, read anew.

    A frame is cut to the width the terminal has then and replaces the one before it; without
    a width it is whole and follows it. Raises PaceError when the seconds or the count asked
    for are no positive number; no frame is written then.
    """
    pace = make_pace(args.seconds, args.count)
    top = None if args.all else TOP

    def read_frame() -> str:
        return framed(status_item(store, top), width())

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
    width: Width = _no_terminal,
    wait: Wait = _no_wait,
) -> int:
    """Read the arguments, locate the record in cwd, run the command and return the exit status.

    The help option needs no record, after a command as alone: it prints the help of the command
    the arguments name. Every other call fails with 2 when there is no record. A write finds the
    git work tree of the record through open_git and is committed there. The lines of status are
    cut to the width of the terminal; without one, as by default, they are whole. Watch writes
    its frames as it goes and waits between two by wait, which by default returns at once; it
    exits with 0 once its count is written or Ctrl-C ends it.
    """
    command_line = build_command_line()
    parser = command_line.parser
    asked = help_asked(argv, command_line)
    if asked is not None:
        write(asked)
        return 0
    args = parser.parse_args(argv)
    match locate(cwd, args.dir, is_dir):
        case Found(path) | Given(path):
            store = within(
                across_worktrees(open_store(path), path, open_git, open_store),
                partial(scope_in, path, open_git),
                partial(worktree_of_item, path, open_git),
            )
            try:
                if args.command == "watch":
                    _watch(args, store, write, wait, width)
                    return 0
                said = _said(args, store, now, path, open_git, width)
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
            write_error(" -- pass --dir PATH\n")
            return 2
        case GivenMissing(path):
            write_error(f"{parser.format_usage()}fgraph: error: --dir {path} is no directory\n")
            return 2
        case _ as unreachable:
            assert_never(unreachable)


def main() -> None:
    """Run the command in the working directory of the process, on its arguments and streams."""
    sys.exit(
        run(
            sys.argv[1:],
            Path.cwd(),
            Path.is_dir,
            sys.stdout.write,
            sys.stderr.write,
            open_store=open_files,
            open_git=open_git,
            now=lambda: datetime.now(UTC),
            width=terminal_width,
            wait=time.sleep,
        )
    )


if __name__ == "__main__":
    main()
