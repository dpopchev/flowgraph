"""The `fgraph` command line: it locates the record, and with no command yet shows the help menu."""

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import assert_never

from flowgraph.record import Found, Given, GivenMissing, IsDir, NotFound, locate

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
    return parser


def run(argv: Sequence[str], cwd: Path, is_dir: IsDir, write: Write, write_error: Write) -> int:
    """Read the arguments, locate the record in cwd and return the exit status.

    The help option needs no record; every other call fails with 2 when there is none.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.help:
        write(parser.format_help())
        return 0
    match locate(cwd, args.dir, is_dir):
        case Found(path) | Given(path):
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
    sys.exit(run(sys.argv[1:], Path.cwd(), Path.is_dir, sys.stdout.write, sys.stderr.write))


if __name__ == "__main__":
    main()
