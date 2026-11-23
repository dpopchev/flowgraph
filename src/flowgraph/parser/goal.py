"""The parser of goal: the Feature whose /goal line is printed, and the hours it is bound to."""

import argparse

from flowgraph.parser.base import Commands, new_command

# The hours a goal is bound to when --hours is not given.
HOURS = "8"


def goal_command(commands: Commands) -> argparse.ArgumentParser:
    """The parser of goal, which prints the /goal line of a Feature."""
    goal = new_command(
        commands,
        "goal",
        "print the /goal line a developer pastes for the work items of a Feature in Backlog",
    )
    goal.add_argument("id", metavar="ID", help="the id of the Feature")
    goal.add_argument(
        "--hours",
        default=HOURS,
        metavar="N",
        help=f"the hours the goal is bound to, a whole number of 1 or more; {HOURS} by default",
    )
    return goal
