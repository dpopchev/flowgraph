"""The parser of start: the item to start, the branch it takes and the agent it is handed to."""

import argparse

from flowgraph.parser.base import Commands, new_command


def start_command(commands: Commands) -> argparse.ArgumentParser:
    """The parser of start, which starts a work item or a Task of it, or a Feature."""
    start = new_command(commands, "start", "start a work item or a Task of it, or a Feature")
    start.add_argument(
        "id", metavar="ID", help="the id of the work item, of the Task or of the Feature"
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
