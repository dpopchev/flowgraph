"""The parser of amend: the item whose parts are rewritten and each part by its own option."""

import argparse

from flowgraph.parser.base import Commands, new_command


def amend_command(commands: Commands) -> argparse.ArgumentParser:
    """The parser of amend, which rewrites parts of a work item, a Feature or a Task in Backlog."""
    amend = new_command(
        commands, "amend", "rewrite parts of a work item, a Feature or a Task in Backlog"
    )
    amend.add_argument(
        "id", metavar="ID", help="the id of the work item, of the Feature or of the Task"
    )
    amend.add_argument("--title", metavar="TEXT", help="what is true once it is completed")
    amend.add_argument("--description", metavar="TEXT", help="free text; a blank one clears it")
    amend.add_argument("--output", metavar="TEXT", help="the expected output, of a Task")
    amend.add_argument(
        "--check",
        metavar="COMMAND",
        help="the command that checks it, of a Task; refused with the development off",
    )
    amend.add_argument("--complexity", metavar="WORD", help="low, medium or high, in Backlog alone")
    amend.add_argument(
        "--criterion",
        action="append",
        metavar="TEXT",
        help="what the user experiences, of a Feature; once per criterion, in place of its own",
    )
    amend.add_argument("--given", metavar="STATE", help="the initial state")
    amend.add_argument("--when", metavar="ACTION", help="the action")
    amend.add_argument("--then", metavar="STATE", help="the expected state")
    amend.add_argument("--observed", metavar="TEXT", help="what happens, of a Bug")
    amend.add_argument("--expected", metavar="TEXT", help="what we wish to see, of a Bug")
    amend.add_argument("--hypothesis", metavar="TEXT", help="the question, of a Spike")
    amend.add_argument(
        "--parent", metavar="ID", help="the Feature to put it under, or none to stand alone"
    )
    amend.add_argument("--realizes", metavar="N", help="the criterion it realizes: N or none")
    amend.add_argument(
        "--depends-on",
        action="append",
        metavar="ID",
        help="a work item it waits for, once per id, in place of its own; none takes them away",
    )
    amend.add_argument(
        "--about",
        action="append",
        metavar="TERM",
        help="a term it is about, once per term, in place of its own; none takes them away",
    )
    return amend
