"""The parsers of note and knowledge: the line a note keeps and the lines the list shows."""

import argparse

from flowgraph.knowledge.document import JSON, TEXT
from flowgraph.parser.base import Commands, new_command

# The summary of note, the help of its ID and of its --progress, each too long for its call.
NOTE = "keep a finding, a decision, a deviation or a progress line on a work item, in any state"
NOTE_ID = "the id of the work item or of the Feature, of a Task too with --progress"
NOTE_PROGRESS = "where the work stands; no knowledge line"
NOTE_SUPERSEDES = (
    "an earlier line this one supersedes, by the ref fgraph knowledge lists, as S-0001#2; "
    "once per line"
)


def note_command(commands: Commands) -> argparse.ArgumentParser:
    """The parser of note, which keeps a line of knowledge or a progress line on an item."""
    note = new_command(commands, "note", NOTE)
    note.add_argument("id", metavar="ID", help=NOTE_ID)
    note.add_argument("--about", action="append", metavar="TERM", help="a term the line is about")
    note.add_argument(
        "--governs", action="append", metavar="PATH", help="a file the line governs; once per file"
    )
    note.add_argument("--supersedes", action="append", metavar="REF", help=NOTE_SUPERSEDES)
    kinds = note.add_mutually_exclusive_group(required=True)
    kinds.add_argument("--finding", metavar="TEXT", help="what the work learned")
    kinds.add_argument("--decision", metavar="TEXT", help="what was decided")
    kinds.add_argument(
        "--deviation", metavar="TEXT", help="a change to what a started item was agreed to do"
    )
    kinds.add_argument("--progress", metavar="TEXT", help=NOTE_PROGRESS)
    marks = note.add_mutually_exclusive_group()
    marks.add_argument(
        "--standing",
        dest="mark",
        action="store_const",
        const="standing",
        help="mark the line as standing: it holds until a later line supersedes it",
    )
    marks.add_argument(
        "--open",
        dest="mark",
        action="store_const",
        const="open",
        help="mark the line as open: not settled yet",
    )
    return note


def knowledge_command(commands: Commands) -> argparse.ArgumentParser:
    """The parser of knowledge, which lists the lines of every work item and Feature."""
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
    knowledge.add_argument(
        "--search", metavar="TEXT", help="list the lines whose text holds this text, in any case"
    )
    knowledge.add_argument(
        "--live",
        action="store_true",
        help="list the live lines alone: those no later line supersedes",
    )
    knowledge.add_argument(
        "--format",
        default=TEXT,
        metavar="FORMAT",
        help=f"the format it prints: {TEXT}, the default, or {JSON}",
    )
    return knowledge
