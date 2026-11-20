"""The `fgraph` command line: with no command yet, every valid call shows the help menu."""

import argparse
import sys
from collections.abc import Callable, Sequence

DESCRIPTION = "flowgraph keeps the record of a project's work."


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
    return parser


def run(argv: Sequence[str], write: Callable[[str], object]) -> int:
    """Read the arguments, write the help menu and return the exit status.

    What `write` returns is ignored, so a stream's `write` and a list's `append` both fit.
    """
    parser = build_parser()
    parser.parse_args(argv)
    write(parser.format_help())
    return 0


def main() -> None:
    """Run the command on the arguments of the process, writing to its standard output."""
    sys.exit(run(sys.argv[1:], sys.stdout.write))


if __name__ == "__main__":
    main()
