"""The pieces every parser of a command is built from: the commands a parser holds and a command.

A command carries a help option of its own, named once here.
"""

import argparse
from typing import Protocol

# The options that ask for help.
HELP = ("-h", "--help")


class Commands(Protocol):
    """The commands a parser holds, as argparse makes them: each is added as a parser of its own."""

    def add_parser(
        self, name: str, *, help: str, add_help: bool, color: bool
    ) -> argparse.ArgumentParser: ...


def new_command(parsers: Commands, name: str, summary: str) -> argparse.ArgumentParser:
    """A command of that name under the parsers, with its help option.

    The help option only marks the call: `run` writes the help through its own writer, where
    argparse's built-in one prints and exits. Color is off so the help is the same text on
    every stream.
    """
    made = parsers.add_parser(name, help=summary, add_help=False, color=False)
    made.add_argument(*HELP, action="store_true", help="show the help of this command and exit")
    return made
