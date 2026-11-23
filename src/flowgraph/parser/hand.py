"""The parser of hand: the started work item and the agent it is handed to."""

import argparse

from flowgraph.parser.base import Commands, new_command


def hand_command(commands: Commands) -> argparse.ArgumentParser:
    """The parser of hand, which hands a started work item to an agent."""
    hand = new_command(commands, "hand", "hand a started work item to another agent")
    hand.add_argument("id", metavar="ID", help="the id of the started work item")
    hand.add_argument(
        "--agent",
        required=True,
        metavar="NAME",
        help=(
            "the agent the work item is handed to, in place of the one it held: one word of at"
            " most 32 letters, digits and . _ : / -; read with the development on"
        ),
    )
    return hand
