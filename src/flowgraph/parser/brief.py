"""The parser of brief: the work item whose brief is printed, and the format it is printed in."""

import argparse

from flowgraph.brief.document import JSON, TEXT
from flowgraph.parser.base import Commands, new_command


def brief_command(commands: Commands) -> argparse.ArgumentParser:
    """The parser of brief, which prints the whole brief of a work item."""
    brief = new_command(
        commands,
        "brief",
        "print the brief of a work item: its text, worktree, Feature, governing lines and terms",
    )
    brief.add_argument("id", metavar="ID", help="the id of the work item, in any state")
    brief.add_argument(
        "--format",
        default=TEXT,
        metavar="FORMAT",
        help=f"the format it prints: {TEXT}, the default, or {JSON}",
    )
    return brief
