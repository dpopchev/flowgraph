"""The `fgraph` command line: it locates the record and runs the command on it.

Without a command it shows the help menu and names the record.
"""

import argparse
import sys
from collections.abc import Callable, Collection, Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import assert_never

from flowgraph import story, upkeep
from flowgraph.record import Found, Given, GivenMissing, IsDir, NotFound, locate
from flowgraph.story import (
    CommitError,
    CompletedAlreadyError,
    EmptyPartError,
    FindStoryRows,
    FindTaskIds,
    ItemIdError,
    LoadStory,
    NoTaskError,
    NotStartedError,
    Now,
    OpenTaskError,
    SaveStory,
    StartedAlreadyError,
    StoryDetail,
    StoryId,
    StoryIdError,
    StoryInBacklogError,
    StoryNotFoundError,
    StoryRow,
    TaskId,
    TaskNotFoundError,
    add_story,
    add_task,
    complete_story,
    complete_task,
    make_commit,
    parse_item_id,
    parse_story_id,
    start_story,
    start_task,
    story_id_text,
    task_id_text,
)
from flowgraph.upkeep import (
    FindUpkeepRows,
    SaveUpkeep,
    UpkeepDetail,
    UpkeepId,
    UpkeepIdError,
    UpkeepNotFoundError,
    UpkeepRow,
    add_upkeep,
    parse_upkeep_id,
    upkeep_id_text,
)

DESCRIPTION = "flowgraph keeps the record of a project's work."

# Write text to a stream; what it returns is ignored, so a stream's write and a list's append fit.
Write = Callable[[str], object]

# The Story of that id as plain data; raises StoryNotFoundError when the record holds none.
FindStoryDetail = Callable[[StoryId], StoryDetail]

# The Upkeep of that id as plain data; raises UpkeepNotFoundError when the record holds none.
FindUpkeepDetail = Callable[[UpkeepId], UpkeepDetail]


@dataclass(frozen=True)
class Store:
    """The reads and writes of one record, each already bound to its directory."""

    find_story_rows: FindStoryRows
    load_story: LoadStory
    find_story_detail: FindStoryDetail
    find_task_ids: FindTaskIds
    save_story: SaveStory
    find_upkeep_rows: FindUpkeepRows
    find_upkeep_detail: FindUpkeepDetail
    save_upkeep: SaveUpkeep


# The store of the record in that directory.
OpenStore = Callable[[Path], Store]


def open_files(record: Path) -> Store:
    """The store of the record in that directory, kept as its files."""
    return Store(
        find_story_rows=partial(story.read_story_rows, record),
        load_story=partial(story.read_story, record),
        find_story_detail=partial(story.read_story_detail, record),
        find_task_ids=partial(story.read_task_ids, record),
        save_story=partial(story.write_story, record),
        find_upkeep_rows=partial(upkeep.read_upkeep_rows, record),
        find_upkeep_detail=partial(upkeep.read_upkeep_detail, record),
        save_upkeep=partial(upkeep.write_upkeep, record),
    )


# The buckets of the flow in their order, each with the states of an item shown in it.
BUCKETS: Sequence[tuple[str, Collection[str]]] = (
    ("Backlog", frozenset({"backlog"})),
    ("InProgress", frozenset({"started"})),
    ("Completed", frozenset({"completed"})),
)

# The refusals of a start, each written as a usage error.
START_REFUSED = (
    ItemIdError,
    StoryNotFoundError,
    TaskNotFoundError,
    NoTaskError,
    StartedAlreadyError,
    StoryInBacklogError,
    CompletedAlreadyError,
)

# The refusals of a complete, each written as a usage error.
COMPLETE_REFUSED = (
    ItemIdError,
    CommitError,
    StoryNotFoundError,
    TaskNotFoundError,
    NotStartedError,
    OpenTaskError,
    CompletedAlreadyError,
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
        "show", help="show a Story with its Tasks, or an Upkeep", add_help=False, color=False
    )
    show.add_argument("id", metavar="ID", help="the id of the Story or of the Upkeep")
    start = commands.add_parser(
        "start", help="start a Story or a Task of it", add_help=False, color=False
    )
    start.add_argument("id", metavar="ID", help="the id of the Story or of the Task")
    complete = commands.add_parser(
        "complete", help="complete a Story or a Task of it in a commit", add_help=False, color=False
    )
    complete.add_argument("id", metavar="ID", help="the id of the Story or of the Task")
    complete.add_argument(
        "--commit", required=True, metavar="SHA", help="the commit that holds its work"
    )
    commands.add_parser(
        "status", help="list the items of the record by bucket", add_help=False, color=False
    )
    return parser


def status_text(rows: Iterable[StoryRow | UpkeepRow]) -> str:
    """The items by bucket, in the order of the flow: a heading with its count, then its items.

    A completed item is listed with its commit.
    """
    listed = list(rows)
    lines: list[str] = []
    for bucket, states in BUCKETS:
        held = [row for row in listed if row.state in states]
        lines.append(f"{bucket} ({len(held)})\n")
        lines.extend(
            f"  {row.id}  {row.title}  {row.commit}\n"
            if row.commit
            else f"  {row.id}  {row.title}\n"
            for row in held
        )
    return "".join(lines)


def show_text(detail: StoryDetail) -> str:
    """The Story with its bucket and its criterion, then its Tasks, one fact per line.

    A description and a commit are listed only when there is one, the bucket of a Task only once
    it has left Backlog.
    """
    bucket = next(name for name, states in BUCKETS if detail.state in states)
    committed = [f"  commit       {detail.commit}\n"] if detail.commit else []
    described = [f"  description  {detail.description}\n"] if detail.description else []
    lines = [
        f"{detail.id}  {detail.title}\n",
        f"  bucket       {bucket}\n",
        *committed,
        *described,
        f"  given        {detail.given}\n",
        f"  when         {detail.when}\n",
        f"  then         {detail.then}\n",
        f"Tasks ({len(detail.tasks)})\n",
    ]
    for task in detail.tasks:
        lines.append(f"  {task.id}  {task.title}\n")
        task_bucket = next(name for name, states in BUCKETS if task.state in states)
        if task_bucket != "Backlog":
            lines.append(f"    bucket           {task_bucket}\n")
        if task.commit:
            lines.append(f"    commit           {task.commit}\n")
        lines.append(f"    expected output  {task.expected_output}\n")
        if task.description:
            lines.append(f"    description      {task.description}\n")
    return "".join(lines)


def show_upkeep_text(detail: UpkeepDetail) -> str:
    """The Upkeep with its bucket and its criterion, one fact per line.

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
    ]
    return "".join(lines)


def _show(item: str, store: Store) -> str:
    """The text of the Story or the Upkeep of that id.

    Raises StoryIdError when the text is neither id, naming it as no Story id, and
    StoryNotFoundError or UpkeepNotFoundError when the record holds no such item.
    """
    try:
        upkeep_id = parse_upkeep_id(item)
    except UpkeepIdError:
        return show_text(store.find_story_detail(parse_story_id(item)))
    return show_upkeep_text(store.find_upkeep_detail(upkeep_id))


def _complete(item: str, sha: str, store: Store, now: Now) -> str:
    """Complete the Story or the Task of that id in the commit of that sha; the line that says so.

    Raises ItemIdError, CommitError, or a refusal of the move (COMPLETE_REFUSED); nothing is saved.
    """
    commit = make_commit(sha)
    match parse_item_id(item):
        case StoryId() as story_id:
            complete_story(
                story_id=story_id,
                commit=commit,
                load_story=store.load_story,
                save_story=store.save_story,
                now=now,
            )
            return f"completed {story_id_text(story_id)} at {commit.sha}\n"
        case TaskId() as task_id:
            holder = complete_task(
                task_id=task_id,
                commit=commit,
                find_story_rows=store.find_story_rows,
                load_story=store.load_story,
                save_story=store.save_story,
                now=now,
            )
            return f"completed {task_id_text(task_id)} of {story_id_text(holder)} at {commit.sha}\n"
        case _ as unreachable:
            assert_never(unreachable)


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
                    written = add_task(
                        parent=args.parent,
                        title=args.title,
                        expected_output=args.output,
                        description=args.description,
                        load_story=store.load_story,
                        find_task_ids=store.find_task_ids,
                        save_story=store.save_story,
                        now=now,
                    )
                except (
                    StoryNotFoundError,
                    StoryIdError,
                    EmptyPartError,
                    CompletedAlreadyError,
                ) as error:
                    write_error(f"{parser.format_usage()}fgraph: error: {error}\n")
                    return 2
                write(f"added {task_id_text(written)} to {args.parent}\n")
                return 0
            if args.command == "complete":
                try:
                    done = _complete(args.id, args.commit, store, now)
                except COMPLETE_REFUSED as error:
                    write_error(f"{parser.format_usage()}fgraph: error: {error}\n")
                    return 2
                write(done)
                return 0
            if args.command == "add" and args.kind == "upkeep":
                try:
                    added_upkeep = add_upkeep(
                        title=args.title,
                        given=args.given,
                        when=args.when,
                        then=args.then,
                        description=args.description,
                        find_upkeep_rows=store.find_upkeep_rows,
                        save_upkeep=store.save_upkeep,
                        now=now,
                    )
                except EmptyPartError as error:
                    write_error(f"{parser.format_usage()}fgraph: error: {error}\n")
                    return 2
                write(f"added {upkeep_id_text(added_upkeep)}\n")
                return 0
            if args.command == "show":
                try:
                    shown = _show(args.id, store)
                except (StoryNotFoundError, StoryIdError, UpkeepNotFoundError) as error:
                    write_error(f"{parser.format_usage()}fgraph: error: {error}\n")
                    return 2
                write(shown)
                return 0
            if args.command == "start":
                try:
                    match parse_item_id(args.id):
                        case StoryId() as story_id:
                            start_story(
                                story_id=story_id,
                                load_story=store.load_story,
                                save_story=store.save_story,
                                now=now,
                            )
                            write(f"started {story_id_text(story_id)}\n")
                        case TaskId() as task_id:
                            holder = start_task(
                                task_id=task_id,
                                find_story_rows=store.find_story_rows,
                                load_story=store.load_story,
                                save_story=store.save_story,
                                now=now,
                            )
                            write(f"started {task_id_text(task_id)} of {story_id_text(holder)}\n")
                        case _ as unreachable:
                            assert_never(unreachable)
                except START_REFUSED as error:
                    write_error(f"{parser.format_usage()}fgraph: error: {error}\n")
                    return 2
                return 0
            if args.command == "add":
                try:
                    added = add_story(
                        title=args.title,
                        given=args.given,
                        when=args.when,
                        then=args.then,
                        description=args.description,
                        find_story_rows=store.find_story_rows,
                        save_story=store.save_story,
                        now=now,
                    )
                except EmptyPartError as error:
                    write_error(f"{parser.format_usage()}fgraph: error: {error}\n")
                    return 2
                write(f"added {story_id_text(added)}\n")
                return 0
            if args.command == "status":
                write(status_text([*store.find_story_rows(), *store.find_upkeep_rows()]))
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
