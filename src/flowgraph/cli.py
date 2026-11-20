"""The `fgraph` command line: it locates the record and runs the command on it.

Without a command it shows the help menu and names the record.
"""

import argparse
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import assert_never

from flowgraph.record import Found, Given, GivenMissing, IsDir, NotFound, locate
from flowgraph.story import Now, ReadStoryRows, WriteStory, read_story_rows, write_story

DESCRIPTION = "flowgraph keeps the record of a project's work."

# Write text to a stream; what it returns is ignored, so a stream's write and a list's append fit.
Write = Callable[[str], object]


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
    read_story_rows: ReadStoryRows,
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
            if args.command is not None:
                raise NotImplementedError(args.command)
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
            read_story_rows=read_story_rows,
            write_story=write_story,
            now=lambda: datetime.now(UTC),
        )
    )


if __name__ == "__main__":
    main()
