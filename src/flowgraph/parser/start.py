"""The parser of start: the item to start, the branch it takes and the agent it is handed to."""

import argparse
from collections.abc import Callable

from flowgraph.parser.base import Commands, new_command

# The id of the top of the Backlog, read anew; it raises the refusal of a start when none is marked.
Top = Callable[[], str]


def start_named(args: argparse.Namespace, top: Top) -> argparse.Namespace:
    """The arguments with the id of the top when a start is given none; the others as they are."""
    if args.command != "start" or args.id is not None:
        return args
    return argparse.Namespace(**{**vars(args), "id": top()})


def start_command(commands: Commands) -> argparse.ArgumentParser:
    """The parser of start, which starts a work item or a Task of it, or a Feature."""
    start = new_command(commands, "start", "start a work item or a Task of it, or a Feature")
    start.add_argument(
        "id",
        metavar="ID",
        nargs="?",
        help=(
            "the id of the work item, of the Task or of the Feature; left out, the first"
            " fgraph status marks as able to start"
        ),
    )
    start.add_argument(
        "--slug",
        metavar="TEXT",
        help=(
            "the words of a work item's branch after its id, instead of its title's first four;"
            " of a Feature, those of its first work item; read with the development on"
        ),
    )
    start.add_argument(
        "--agent",
        metavar="NAME",
        help=(
            "the agent a work item is handed to, one word of at most 32 letters, digits and"
            " . _ : / -; of a Feature, its first work item; read with the development on"
        ),
    )
    return start
