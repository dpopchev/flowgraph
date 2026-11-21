"""The `fgraph` command line: it locates the record and runs the command on it.

Without a command it shows the help menu and names the record.
"""

import argparse
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import assert_never

from flowgraph.branch import GitError, SlugError
from flowgraph.commit import OpenGit, Said, commit_written, open_git
from flowgraph.criterion import CommitError, EmptyPartError
from flowgraph.item import (
    ItemIdError,
    OpenStore,
    Store,
    Written,
    add_item,
    amend_item,
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
from flowgraph.work_item import (
    Amendment,
    NoPartError,
    WorkItemIdError,
    WorkItemNotFoundError,
)

__all__ = ["Store", "open_files", "open_git", "run"]

DESCRIPTION = "flowgraph keeps the record of a project's work."

# Write text to a stream; what it returns is ignored, so a stream's write and a list's append fit.
Write = Callable[[str], object]

# The refusals of a command, each written as a usage error; a git step refused among them.
REFUSED = (
    ItemIdError,
    WorkItemIdError,
    SlugError,
    GitError,
    CommitError,
    EmptyPartError,
    NoPartError,
    WorkItemNotFoundError,
    TaskNotFoundError,
    NoTaskError,
    NotStartedError,
    StartedAlreadyError,
    ItemInBacklogError,
    OpenTaskError,
    CompletedAlreadyError,
    NotInBacklogError,
    SameItemError,
)


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
    amend = commands.add_parser(
        "amend", help="rewrite parts of a work item in Backlog", add_help=False, color=False
    )
    amend.add_argument("id", metavar="ID", help="the id of the Story or of the Upkeep")
    amend.add_argument("--title", metavar="TEXT", help="what is true once it is completed")
    amend.add_argument("--description", metavar="TEXT", help="free text; a blank one clears it")
    amend.add_argument("--given", metavar="STATE", help="the initial state")
    amend.add_argument("--when", metavar="ACTION", help="the action")
    amend.add_argument("--then", metavar="STATE", help="the expected state")
    show = commands.add_parser(
        "show", help="show a Story or an Upkeep with its Tasks", add_help=False, color=False
    )
    show.add_argument("id", metavar="ID", help="the id of the Story or of the Upkeep")
    start = commands.add_parser(
        "start", help="start a work item or a Task of it", add_help=False, color=False
    )
    start.add_argument("id", metavar="ID", help="the id of the Story, the Upkeep or the Task")
    start.add_argument(
        "--slug",
        metavar="TEXT",
        help="the words of a work item's branch after its id, instead of its title's first four",
    )
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


def _written(args: argparse.Namespace, store: Store, now: Now) -> Written | None:
    """Make the write the arguments name on the store; None when they name a view or no command.

    Raises the refusal of the write; nothing is saved then.
    """
    match args.command:
        case "add" if args.kind == "task":
            return write_task(args.parent, args.title, args.output, args.description, store, now)
        case "add":
            criterion = (args.given, args.when, args.then)
            kind = kind_named(args.kind)
            return add_item(kind, args.title, criterion, args.description, store, now)
        case "amend":
            parts = Amendment(args.title, args.description, args.given, args.when, args.then)
            return amend_item(args.id, parts, store)
        case "complete":
            return complete_item(args.id, args.commit, store, now)
        case "start":
            return start_item(args.id, args.slug, store, now)
        case "reorder":
            return reorder_item(args.id, args.before, store)
        case _:
            return None


def _said(
    args: argparse.Namespace, store: Store, now: Now, record: Path, open_git: OpenGit
) -> Said | None:
    """Run the command the arguments name on the record; None when they name none.

    A write is committed once it is made. Raises the refusal of the command, a git step refused
    among them.
    """
    written = _written(args, store, now)
    if written is not None:
        return commit_written(written, store, record, open_git)
    match args.command:
        case "show":
            return Said(show_item(args.id, store))
        case "status":
            return Said(status_item(store))
        case _:
            return None


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
) -> int:
    """Read the arguments, locate the record in cwd, run the command and return the exit status.

    The help option needs no record; every other call fails with 2 when there is none. A write
    finds the git work tree of the record through open_git and is committed there.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.help:
        write(parser.format_help())
        return 0
    match locate(cwd, args.dir, is_dir):
        case Found(path) | Given(path):
            try:
                said = _said(args, open_store(path), now, path, open_git)
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
        )
    )


if __name__ == "__main__":
    main()
