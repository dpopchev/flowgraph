"""The `fgraph` command line: it locates the record and runs the command on it.

Without a command it shows the help menu and names the record.
"""

import argparse
import sys
from collections.abc import Callable, Collection, Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import assert_never

from flowgraph import story
from flowgraph.record import Found, Given, GivenMissing, IsDir, NotFound, locate
from flowgraph.story import (
    EmptyPartError,
    Now,
    ReadStory,
    ReadStoryDetail,
    ReadStoryRows,
    ReadTaskIds,
    StoryDetail,
    StoryIdError,
    StoryNotFoundError,
    StoryRow,
    WriteStory,
    add_story,
    add_task,
    parse_story_id,
    story_id_text,
    task_id_text,
)

DESCRIPTION = "flowgraph keeps the record of a project's work."

# Write text to a stream; what it returns is ignored, so a stream's write and a list's append fit.
Write = Callable[[str], object]

# The buckets of the flow in their order, each with the states of an item shown in it. No state
# leads to InProgress or Completed yet.
BUCKETS: Sequence[tuple[str, Collection[str]]] = (
    ("Backlog", frozenset({"backlog"})),
    ("InProgress", frozenset()),
    ("Completed", frozenset()),
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
        "task", help="a deliverable of a Story, with its output", add_help=False, color=False
    )
    task.add_argument("title", metavar="TITLE", help="a verb, the artifact and its target state")
    task.add_argument("--parent", required=True, metavar="ID", help="the Story it is written for")
    task.add_argument("--output", required=True, metavar="TEXT", help="the expected output")
    task.add_argument("--description", default="", metavar="TEXT", help="free text, optional")
    show = commands.add_parser(
        "show", help="show a Story with its Tasks", add_help=False, color=False
    )
    show.add_argument("id", metavar="ID", help="the id of the Story")
    commands.add_parser(
        "status", help="list the items of the record by bucket", add_help=False, color=False
    )
    return parser


def status_text(rows: Iterable[StoryRow]) -> str:
    """The items by bucket, in the order of the flow: a heading with its count, then its items."""
    listed = list(rows)
    lines: list[str] = []
    for bucket, states in BUCKETS:
        held = [row for row in listed if row.state in states]
        lines.append(f"{bucket} ({len(held)})\n")
        lines.extend(f"  {row.id}  {row.title}\n" for row in held)
    return "".join(lines)


def show_text(detail: StoryDetail) -> str:
    """The Story with its bucket and its criterion, then its Tasks, one fact per line.

    A description is listed only when there is one.
    """
    bucket = next(name for name, states in BUCKETS if detail.state in states)
    described = [f"  description  {detail.description}\n"] if detail.description else []
    lines = [
        f"{detail.id}  {detail.title}\n",
        f"  bucket       {bucket}\n",
        *described,
        f"  given        {detail.given}\n",
        f"  when         {detail.when}\n",
        f"  then         {detail.then}\n",
        f"Tasks ({len(detail.tasks)})\n",
    ]
    for task in detail.tasks:
        lines.append(f"  {task.id}  {task.title}\n")
        lines.append(f"    expected output  {task.expected_output}\n")
        if task.description:
            lines.append(f"    description      {task.description}\n")
    return "".join(lines)


def run(
    argv: Sequence[str],
    cwd: Path,
    is_dir: IsDir,
    write: Write,
    write_error: Write,
    *,
    read_story_rows: ReadStoryRows,
    read_story: ReadStory,
    read_story_detail: ReadStoryDetail,
    read_task_ids: ReadTaskIds,
    write_story: WriteStory,
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
            if args.command == "add" and args.kind == "task":
                try:
                    written = add_task(
                        parent=args.parent,
                        title=args.title,
                        expected_output=args.output,
                        description=args.description,
                        load_story=lambda story_id: read_story(path, story_id),
                        find_task_ids=lambda: read_task_ids(path),
                        save_story=lambda changed: write_story(path, changed),
                        now=now,
                    )
                except (StoryNotFoundError, StoryIdError, EmptyPartError) as error:
                    write_error(f"{parser.format_usage()}fgraph: error: {error}\n")
                    return 2
                write(f"added {task_id_text(written)} to {args.parent}\n")
                return 0
            if args.command == "show":
                try:
                    detail = read_story_detail(path, parse_story_id(args.id))
                except (StoryNotFoundError, StoryIdError) as error:
                    write_error(f"{parser.format_usage()}fgraph: error: {error}\n")
                    return 2
                write(show_text(detail))
                return 0
            if args.command == "add":
                try:
                    added = add_story(
                        title=args.title,
                        given=args.given,
                        when=args.when,
                        then=args.then,
                        description=args.description,
                        find_story_rows=lambda: read_story_rows(path),
                        save_story=lambda new: write_story(path, new),
                        now=now,
                    )
                except EmptyPartError as error:
                    write_error(f"{parser.format_usage()}fgraph: error: {error}\n")
                    return 2
                write(f"added {story_id_text(added)}\n")
                return 0
            if args.command == "status":
                write(status_text(read_story_rows(path)))
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
            read_story_rows=story.read_story_rows,
            read_story=story.read_story,
            read_story_detail=story.read_story_detail,
            read_task_ids=story.read_task_ids,
            write_story=story.write_story,
            now=lambda: datetime.now(UTC),
        )
    )


if __name__ == "__main__":
    main()
