"""The arguments of the `fgraph` command line: its commands, their options and their help."""

import argparse
from pathlib import Path

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
    parser.add_argument(
        "-d",
        "--dir",
        type=Path,
        metavar="PATH",
        help="the record directory, instead of .fgraph/ or else fgraph/ in this directory",
    )
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")
    add = commands.add_parser("add", help="add an item to the record", add_help=False, color=False)
    kinds = add.add_subparsers(dest="kind", metavar="KIND", required=True)
    story = kinds.add_parser(
        "story", help="new behavior, with its one Given / When / Then", add_help=False, color=False
    )
    story.add_argument("title", metavar="TITLE", help="what is true once the Story is completed")
    story.add_argument("--given", required=True, metavar="STATE", help="the initial state")
    story.add_argument("--when", required=True, metavar="ACTION", help="the action")
    story.add_argument("--then", required=True, metavar="STATE", help="the expected state")
    story.add_argument("--description", default="", metavar="TEXT", help="free text, optional")
    task = kinds.add_parser(
        "task", help="a deliverable of a work item, with its output", add_help=False, color=False
    )
    task.add_argument("title", metavar="TITLE", help="a verb, the artifact and its target state")
    task.add_argument(
        "--parent", required=True, metavar="ID", help="the work item it is written for"
    )
    task.add_argument("--output", required=True, metavar="TEXT", help="the expected output")
    task.add_argument("--description", default="", metavar="TEXT", help="free text, optional")
    upkeep = kinds.add_parser(
        "upkeep",
        help="work that keeps a behavior, with its one Given / When / Then",
        add_help=False,
        color=False,
    )
    upkeep.add_argument("title", metavar="TITLE", help="what is true once it is completed")
    upkeep.add_argument("--given", required=True, metavar="STATE", help="the initial state")
    upkeep.add_argument("--when", required=True, metavar="ACTION", help="the action that runs")
    upkeep.add_argument("--then", required=True, metavar="STATE", help="what still holds")
    upkeep.add_argument("--description", default="", metavar="TEXT", help="free text, optional")
    bug = kinds.add_parser(
        "bug",
        help="a behavior that fails, with what is observed and what is expected",
        add_help=False,
        color=False,
    )
    bug.add_argument("title", metavar="TITLE", help="what is true once the Bug is completed")
    bug.add_argument("--observed", required=True, metavar="TEXT", help="what happens")
    bug.add_argument("--expected", required=True, metavar="TEXT", help="what we wish to see")
    bug.add_argument("--description", default="", metavar="TEXT", help="free text, optional")
    spike = kinds.add_parser(
        "spike", help="a question to answer, with its hypothesis", add_help=False, color=False
    )
    spike.add_argument("title", metavar="TITLE", help="what is settled once it is completed")
    spike.add_argument("--hypothesis", required=True, metavar="TEXT", help="a yes/no question")
    spike.add_argument("--description", default="", metavar="TEXT", help="free text, optional")
    amend = commands.add_parser(
        "amend", help="rewrite parts of a work item in Backlog", add_help=False, color=False
    )
    amend.add_argument("id", metavar="ID", help="the id of the work item")
    amend.add_argument("--title", metavar="TEXT", help="what is true once it is completed")
    amend.add_argument("--description", metavar="TEXT", help="free text; a blank one clears it")
    amend.add_argument("--given", metavar="STATE", help="the initial state")
    amend.add_argument("--when", metavar="ACTION", help="the action")
    amend.add_argument("--then", metavar="STATE", help="the expected state")
    amend.add_argument("--observed", metavar="TEXT", help="what happens, of a Bug")
    amend.add_argument("--expected", metavar="TEXT", help="what we wish to see, of a Bug")
    amend.add_argument("--hypothesis", metavar="TEXT", help="the question, of a Spike")
    show = commands.add_parser(
        "show", help="show a work item with its Tasks", add_help=False, color=False
    )
    show.add_argument("id", metavar="ID", help="the id of the work item")
    start = commands.add_parser(
        "start", help="start a work item or a Task of it", add_help=False, color=False
    )
    start.add_argument("id", metavar="ID", help="the id of the work item or of the Task")
    start.add_argument(
        "--slug",
        metavar="TEXT",
        help="the words of a work item's branch after its id, instead of its title's first four",
    )
    block = commands.add_parser(
        "block", help="block a started Task that cannot go on", add_help=False, color=False
    )
    block.add_argument("id", metavar="ID", help="the id of the Task")
    block.add_argument("--reason", required=True, metavar="TEXT", help="why it cannot go on")
    block.add_argument(
        "--waiting-on", required=True, metavar="TEXT", help="who or what it waits on"
    )
    unblock = commands.add_parser(
        "unblock", help="take a blocked Task back to started", add_help=False, color=False
    )
    unblock.add_argument("id", metavar="ID", help="the id of the Task")
    complete = commands.add_parser(
        "complete",
        help="complete a work item or a Task of it in a commit",
        add_help=False,
        color=False,
    )
    complete.add_argument("id", metavar="ID", help="the id of the work item or of the Task")
    complete.add_argument(
        "--commit", required=True, metavar="SHA", help="the commit that holds its work"
    )
    complete.add_argument(
        "--decision", metavar="TEXT", help="what answers the hypothesis, of a Spike"
    )
    land = commands.add_parser(
        "land",
        help="land a started work item on main: merge its branch and complete it",
        add_help=False,
        color=False,
    )
    land.add_argument("id", metavar="ID", help="the id of the work item")
    land.add_argument(
        "--message", required=True, metavar="TEXT", help="the message of the merge commit"
    )
    land.add_argument("--decision", metavar="TEXT", help="what answers the hypothesis, of a Spike")
    remove = commands.add_parser(
        "remove",
        help="remove a work item in Backlog, kept with its reason",
        add_help=False,
        color=False,
    )
    remove.add_argument("id", metavar="ID", help="the id of the work item")
    remove.add_argument("--reason", required=True, metavar="TEXT", help="why it is removed")
    reorder = commands.add_parser(
        "reorder",
        help="put a work item of the Backlog before another",
        add_help=False,
        color=False,
    )
    reorder.add_argument("id", metavar="ID", help="the id of the work item to move")
    reorder.add_argument(
        "--before", required=True, metavar="ID", help="the work item it is listed right above"
    )
    commands.add_parser(
        "status", help="list the items of the record by bucket", add_help=False, color=False
    )
    return parser
