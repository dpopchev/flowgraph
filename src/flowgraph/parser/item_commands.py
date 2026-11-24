"""The parser of each command that reads or moves an item: all but add, config, goal and hand."""

import argparse

from flowgraph.graph import JSON
from flowgraph.parser.amend import amend_command
from flowgraph.parser.base import Commands, new_command
from flowgraph.parser.brief import brief_command
from flowgraph.parser.knowledge import knowledge_command, note_command
from flowgraph.parser.start import start_command
from flowgraph.status import document
from flowgraph.term import KINDS

# The items status lists under one heading, unless every one is asked for.
TOP = 5

# The seconds watch waits between two frames, unless others are given.
EVERY = 5

# The answers to a hypothesis a Spike is completed with.
ANSWERS = ("yes", "no")


def item_commands(commands: Commands) -> dict[str, argparse.ArgumentParser]:
    """The parser of each command that reads or moves an item of the record, under its name."""
    amend = amend_command(commands)
    show = new_command(commands, "show", "show a work item with its Tasks, a Feature or a term")
    show.add_argument(
        "id",
        metavar="ID",
        help="the id of the work item or of the Feature, or the name of the term",
    )
    about = new_command(
        commands, "about", "list the links of a work item or a Feature, by relation"
    )
    about.add_argument("id", metavar="ID", help="the id of the work item or of the Feature")
    brief = brief_command(commands)
    start = start_command(commands)
    block = new_command(commands, "block", "block a started work item, Task or Feature")
    block.add_argument("id", metavar="ID", help="the id of the work item, Task or Feature")
    block.add_argument("--reason", required=True, metavar="TEXT", help="why it cannot go on")
    block.add_argument(
        "--waiting-on", required=True, metavar="TEXT", help="who or what it waits on"
    )
    unblock = new_command(commands, "unblock", "take a blocked work item, Task or Feature back")
    unblock.add_argument("id", metavar="ID", help="the id of the work item, Task or Feature")
    complete = new_command(
        commands, "complete", "complete a work item or a Task of it, or a Feature left done"
    )
    complete.add_argument(
        "id", metavar="ID", help="the id of the work item, of the Task or of the Feature"
    )
    complete.add_argument(
        "--commit",
        metavar="SHA",
        help="the commit that holds its work: needed with the development on, optional with it off",
    )
    complete.add_argument(
        "--decision", metavar="TEXT", help="what answers the hypothesis, of a Spike"
    )
    complete.add_argument(
        "--answer", choices=ANSWERS, help="the yes or no of the hypothesis, of a Spike"
    )
    land = new_command(
        commands,
        "land",
        "land a started work item on main: merge its branch, run its gate and complete it",
    )
    land.add_argument("id", metavar="ID", help="the id of the work item")
    land.add_argument(
        "--message",
        metavar="TEXT",
        help="the message of the commit the landing makes: needed by merge-commit and by squash",
    )
    land.add_argument("--decision", metavar="TEXT", help="what answers the hypothesis, of a Spike")
    land.add_argument(
        "--answer", choices=ANSWERS, help="the yes or no of the hypothesis, of a Spike"
    )
    remove = new_command(
        commands, "remove", "remove a work item, a Task or a Feature, kept with its reason"
    )
    remove.add_argument("id", metavar="ID", help="the id of the work item, Task or Feature")
    remove.add_argument("--reason", metavar="TEXT", help="why it is removed")
    remove.add_argument(
        "--superseded-by",
        metavar="ID",
        help="the work item that supersedes it, in place of the reason or beside it",
    )
    note = note_command(commands)
    verify = new_command(
        commands, "verify", "keep the answer of the closing of a completed Story, Bug or Upkeep"
    )
    verify.add_argument("id", metavar="ID", help="the id of the completed work item")
    answers = verify.add_mutually_exclusive_group(required=True)
    answers.add_argument(
        "--yes", metavar="TEXT", help="the criterion holds on main: what the run of it printed"
    )
    answers.add_argument(
        "--no",
        metavar="TEXT",
        help="it does not hold: what the run printed, the observed of the Bug it files",
    )
    release = new_command(
        commands, "release", "tag the head of main with its next v* version, annotated"
    )
    release.add_argument(
        "--version",
        metavar="VERSION",
        help="the version to tag, as v1.0.0, instead of the next one the completed work names",
    )
    knowledge = knowledge_command(commands)
    terms = new_command(commands, "terms", "list the terms of the record with their meanings")
    graph = new_command(commands, "graph", "print the nodes and typed edges of the record")
    graph.add_argument(
        "--format",
        default=JSON,
        metavar="FORMAT",
        help=f"the format it prints: {JSON}, the default",
    )
    relate = new_command(commands, "relate", "relate a term to another: is-a or part-of")
    relate.add_argument("first", metavar="TERM", help="the term that is a kind or a part")
    relate.add_argument("kind", metavar="KIND", help=f"the kind of relation: {' or '.join(KINDS)}")
    relate.add_argument("second", metavar="TERM", help="the term it is a kind of or part of")
    reorder = new_command(
        commands, "reorder", "put a work item or a Feature of the Backlog before another"
    )
    reorder.add_argument(
        "id", metavar="ID", help="the id of the work item or of the Feature to move"
    )
    reorder.add_argument(
        "--before",
        required=True,
        metavar="ID",
        help="the work item or the Feature it is listed right above",
    )
    status = new_command(commands, "status", "list the items of the record by bucket")
    status.add_argument(
        "--all",
        action="store_true",
        help=f"list every item, instead of the top {TOP} under each heading; {document.JSON} lists"
        " every item whether or not it is given",
    )
    status.add_argument(
        "--format",
        default=document.TEXT,
        metavar="FORMAT",
        help=f"the format it prints: {document.TEXT}, the default, or {document.JSON}",
    )
    watch = new_command(
        commands, "watch", "follow the record live: redraw its status every interval"
    )
    watch.add_argument(
        "-n",
        dest="seconds",
        type=float,
        default=EVERY,
        metavar="SECS",
        help=f"the seconds between two frames, instead of {EVERY}",
    )
    watch.add_argument(
        "--count", type=int, metavar="N", help="end after that many frames, instead of at Ctrl-C"
    )
    watch.add_argument(
        "--all",
        action="store_true",
        help=f"list every item, instead of the top {TOP} under each heading",
    )
    return {
        "amend": amend,
        "show": show,
        "about": about,
        "brief": brief,
        "start": start,
        "block": block,
        "unblock": unblock,
        "complete": complete,
        "land": land,
        "remove": remove,
        "note": note,
        "verify": verify,
        "release": release,
        "knowledge": knowledge,
        "terms": terms,
        "graph": graph,
        "relate": relate,
        "reorder": reorder,
        "status": status,
        "watch": watch,
    }
