"""The parser of each command that reads or moves an item of the record: all but add and config."""

import argparse

from flowgraph.graph import JSON
from flowgraph.parser.base import Commands, new_command
from flowgraph.term import KINDS

# The items status lists under one heading, unless every one is asked for.
TOP = 5

# The seconds watch waits between two frames, unless others are given.
EVERY = 5


def item_commands(commands: Commands) -> dict[str, argparse.ArgumentParser]:
    """The parser of each command that reads or moves an item of the record, under its name."""
    amend = new_command(commands, "amend", "rewrite parts of a work item or a Feature in Backlog")
    amend.add_argument("id", metavar="ID", help="the id of the work item or of the Feature")
    amend.add_argument("--title", metavar="TEXT", help="what is true once it is completed")
    amend.add_argument("--description", metavar="TEXT", help="free text; a blank one clears it")
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
    block = new_command(commands, "block", "block a started Task or Feature that cannot go on")
    block.add_argument("id", metavar="ID", help="the id of the Task or of the Feature")
    block.add_argument("--reason", required=True, metavar="TEXT", help="why it cannot go on")
    block.add_argument(
        "--waiting-on", required=True, metavar="TEXT", help="who or what it waits on"
    )
    unblock = new_command(commands, "unblock", "take a blocked Task or Feature back to started")
    unblock.add_argument("id", metavar="ID", help="the id of the Task or of the Feature")
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
    land = new_command(
        commands,
        "land",
        "land a started work item on main: merge its branch, run its gate and complete it",
    )
    land.add_argument("id", metavar="ID", help="the id of the work item")
    land.add_argument(
        "--message",
        metavar="TEXT",
        help="the message of the commit the landing makes: needed unless it lands by fast-forward",
    )
    land.add_argument("--decision", metavar="TEXT", help="what answers the hypothesis, of a Spike")
    remove = new_command(
        commands, "remove", "remove a work item or a Feature in Backlog, kept with its reason"
    )
    remove.add_argument("id", metavar="ID", help="the id of the work item or of the Feature")
    remove.add_argument("--reason", metavar="TEXT", help="why it is removed")
    remove.add_argument(
        "--superseded-by",
        metavar="ID",
        help="the work item that supersedes it, in place of the reason or beside it",
    )
    note = new_command(
        commands, "note", "keep a finding, a decision or a deviation on a work item, in any state"
    )
    note.add_argument("id", metavar="ID", help="the id of the work item")
    note.add_argument("--about", action="append", metavar="TERM", help="a term the line is about")
    note.add_argument(
        "--governs", action="append", metavar="PATH", help="a file the line governs; once per file"
    )
    kinds = note.add_mutually_exclusive_group(required=True)
    kinds.add_argument("--finding", metavar="TEXT", help="what the work learned")
    kinds.add_argument("--decision", metavar="TEXT", help="what was decided")
    kinds.add_argument(
        "--deviation", metavar="TEXT", help="a change to what a started item was agreed to do"
    )
    verify = new_command(
        commands, "verify", "keep the answer of the closing of a completed Story, Bug or Upkeep"
    )
    verify.add_argument("id", metavar="ID", help="the id of the completed work item")
    verify.add_argument(
        "--yes",
        required=True,
        metavar="TEXT",
        help="the criterion holds on main: what the run of it printed",
    )
    knowledge = new_command(
        commands,
        "knowledge",
        "list the knowledge lines of every work item and Feature, newest first",
    )
    knowledge.add_argument(
        "--kind",
        metavar="KIND",
        help="list the lines of one kind alone: finding, decision or deviation",
    )
    knowledge.add_argument("--about", metavar="TERM", help="list the lines about one term alone")
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
        help=f"list every item, instead of the top {TOP} under each heading",
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
        "start": start,
        "block": block,
        "unblock": unblock,
        "complete": complete,
        "land": land,
        "remove": remove,
        "note": note,
        "verify": verify,
        "knowledge": knowledge,
        "terms": terms,
        "graph": graph,
        "relate": relate,
        "reorder": reorder,
        "status": status,
        "watch": watch,
    }
