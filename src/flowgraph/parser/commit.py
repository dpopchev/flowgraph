"""The parser of commit: the work of a started Task, committed."""

import argparse

from flowgraph.parser.base import Commands, new_command


def commit_command(commands: Commands) -> argparse.ArgumentParser:
    """The parser of commit, which commits the files changed that the brief of a Task names."""
    commit = new_command(
        commands,
        "commit",
        "commit the work of a started Task: the files changed that its brief names",
    )
    commit.add_argument("id", metavar="ID", help="the id of the started Task")
    commit.add_argument(
        "--message",
        required=True,
        metavar="TEXT",
        help=(
            "the subject of the commit, its type word included, as fix: name the gate; the ids"
            " of the work item and of the Task are put at its end"
        ),
    )
    return commit
