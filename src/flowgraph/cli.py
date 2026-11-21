"""The `fgraph` command line: it locates the record and runs the command on it.

Without a command it shows the help menu and names the record.
"""

import argparse
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import assert_never

from flowgraph.criterion import CommitError, EmptyPartError
from flowgraph.item import (
    ItemIdError,
    OpenStore,
    Store,
    add_item,
    complete_item,
    kind_named,
    open_files,
    reorder_item,
    show_item,
    start_item,
    status_item,
    write_task,
)
from flowgraph.queue import NotInBacklogError, SameItemError
from flowgraph.record import Found, Given, GivenMissing, IsDir, NotFound, Now, locate
from flowgraph.task import (
    CompletedAlreadyError,
    ItemInBacklogError,
    NoTaskError,
    NotStartedError,
    OpenTaskError,
    StartedAlreadyError,
    TaskNotFoundError,
)
from flowgraph.work_item import WorkItemIdError, WorkItemNotFoundError

__all__ = ["Store", "open_files", "run"]

DESCRIPTION = "flowgraph keeps the record of a project's work."

# Write text to a stream; what it returns is ignored, so a stream's write and a list's append fit.
Write = Callable[[str], object]

# The refusals of a start, each written as a usage error.
START_REFUSED = (
    ItemIdError,
    WorkItemNotFoundError,
    TaskNotFoundError,
    NoTaskError,
    StartedAlreadyError,
    ItemInBacklogError,
    CompletedAlreadyError,
)

# The refusals of a complete, each written as a usage error.
COMPLETE_REFUSED = (
    ItemIdError,
    CommitError,
    WorkItemNotFoundError,
    TaskNotFoundError,
    NotStartedError,
    OpenTaskError,
    CompletedAlreadyError,
)

# The refusals of a reorder, each written as a usage error.
REORDER_REFUSED = (WorkItemIdError, NotInBacklogError, SameItemError)


def build_parser() -> argparse.ArgumentParser:
    """The parser of the command line, its help text included.

    The help option only marks the call: `run` writes the menu through its own writer, where
    argparse's built-in one prints and exits. Color is off so the menu is the same text on
    every stream.
    """
    parser = argparse.ArgumentParser(
        prog="fgraph", description=DESCRIPTION, add_help=False, color=False
    )
    parser.add_argument("-h", "--help", action="store_true", help="show this help menu and exit")
    parser.add_argument(
        "-d",
        "--dir",
        type=Path,
        metavar="PATH",
        help="the record directory, instead of .fgraph/ or else fgraph/ in this directory",
    )
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")
    add = commands.add_parser("add", help="add an item to the record", add_help=False, color=False)
    kinds = add.add_subparsers(dest="kind", metavar="KIND", required=True)
    story = kinds.add_parser(
        "story", help="new behavior, with its one Given / When / Then", add_help=False, color=False
    )
    story.add_argument("title", metavar="TITLE", help="what is true once the Story is completed")
    story.add_argument("--given", required=True, metavar="STATE", help="the initial state")
    story.add_argument("--when", required=True, metavar="ACTION", help="the action")
    story.add_argument("--then", required=True, metavar="STATE", help="the expected state")
    story.add_argument("--description", default="", metavar="TEXT", help="free text, optional")
    task = kinds.add_parser(
        "task", help="a deliverable of a work item, with its output", add_help=False, color=False
    )
    task.add_argument("title", metavar="TITLE", help="a verb, the artifact and its target state")
    task.add_argument(
        "--parent", required=True, metavar="ID", help="the Story or Upkeep it is written for"
    )
    task.add_argument("--output", required=True, metavar="TEXT", help="the expected output")
    task.add_argument("--description", default="", metavar="TEXT", help="free text, optional")
    upkeep = kinds.add_parser(
        "upkeep",
        help="work that keeps a behavior, with its one Given / When / Then",
        add_help=False,
        color=False,
    )
    upkeep.add_argument("title", metavar="TITLE", help="what is true once it is completed")
    upkeep.add_argument("--given", required=True, metavar="STATE", help="the initial state")
    upkeep.add_argument("--when", required=True, metavar="ACTION", help="the action that runs")
    upkeep.add_argument("--then", required=True, metavar="STATE", help="what still holds")
    upkeep.add_argument("--description", default="", metavar="TEXT", help="free text, optional")
    show = commands.add_parser(
        "show", help="show a Story or an Upkeep with its Tasks", add_help=False, color=False
    )
    show.add_argument("id", metavar="ID", help="the id of the Story or of the Upkeep")
    start = commands.add_parser(
        "start", help="start a work item or a Task of it", add_help=False, color=False
    )
    start.add_argument("id", metavar="ID", help="the id of the Story, the Upkeep or the Task")
    complete = commands.add_parser(
        "complete",
        help="complete a work item or a Task of it in a commit",
        add_help=False,
        color=False,
    )
    complete.add_argument("id", metavar="ID", help="the id of the Story, the Upkeep or the Task")
    complete.add_argument(
        "--commit", required=True, metavar="SHA", help="the commit that holds its work"
    )
    reorder = commands.add_parser(
        "reorder",
        help="put a work item of the Backlog before another",
        add_help=False,
        color=False,
    )
    reorder.add_argument("id", metavar="ID", help="the id of the work item to move")
    reorder.add_argument(
        "--before", required=True, metavar="ID", help="the work item it is listed right above"
    )
    commands.add_parser(
        "status", help="list the items of the record by bucket", add_help=False, color=False
    )
    return parser


def run(
    argv: Sequence[str],
    cwd: Path,
    is_dir: IsDir,
    write: Write,
    write_error: Write,
    *,
    open_store: OpenStore,
    now: Now,
) -> int:
    """Read the arguments, locate the record in cwd, run the command and return the exit status.

    The help option needs no record; every other call fails with 2 when there is none.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.help:
        write(parser.format_help())
        return 0
    match locate(cwd, args.dir, is_dir):
        case Found(path) | Given(path):
            store = open_store(path)
            if args.command == "add" and args.kind == "task":
                try:
                    written = write_task(
                        args.parent, args.title, args.output, args.description, store, now
                    )
                except (
                    WorkItemNotFoundError,
                    WorkItemIdError,
                    EmptyPartError,
                    CompletedAlreadyError,
                ) as error:
                    write_error(f"{parser.format_usage()}fgraph: error: {error}\n")
                    return 2
                write(written)
                return 0
            if args.command == "complete":
                try:
                    done = complete_item(args.id, args.commit, store, now)
                except COMPLETE_REFUSED as error:
                    write_error(f"{parser.format_usage()}fgraph: error: {error}\n")
                    return 2
                write(done)
                return 0
            if args.command == "show":
                try:
                    shown = show_item(args.id, store)
                except (WorkItemNotFoundError, WorkItemIdError) as error:
                    write_error(f"{parser.format_usage()}fgraph: error: {error}\n")
                    return 2
                write(shown)
                return 0
            if args.command == "start":
                try:
                    begun = start_item(args.id, store, now)
                except START_REFUSED as error:
                    write_error(f"{parser.format_usage()}fgraph: error: {error}\n")
                    return 2
                write(begun)
                return 0
            if args.command == "add":
                criterion = (args.given, args.when, args.then)
                kind = kind_named(args.kind)
                try:
                    added = add_item(kind, args.title, criterion, args.description, store, now)
                except EmptyPartError as error:
                    write_error(f"{parser.format_usage()}fgraph: error: {error}\n")
                    return 2
                write(added)
                return 0
            if args.command == "reorder":
                try:
                    moved = reorder_item(args.id, args.before, store)
                except REORDER_REFUSED as error:
                    write_error(f"{parser.format_usage()}fgraph: error: {error}\n")
                    return 2
                write(moved)
                return 0
            if args.command == "status":
                write(status_item(store))
                return 0
            write(parser.format_help())
            write(f"record: {path}\n")
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
            now=lambda: datetime.now(UTC),
        )
    )


if __name__ == "__main__":
    main()
