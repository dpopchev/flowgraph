"""The parser of each kind of item `fgraph add` takes: a Story, a Task, an Upkeep, a Bug, a Spike,
a Feature and a term."""

import argparse

from flowgraph.parser_base import Commands, new_command


def add_kinds(kinds: Commands) -> dict[str, argparse.ArgumentParser]:
    """The parser of each kind of item `fgraph add` takes, under its name."""
    story = new_command(kinds, "story", "new behavior, with its one Given / When / Then")
    story.add_argument("title", metavar="TITLE", help="what is true once the Story is completed")
    story.add_argument("--given", required=True, metavar="STATE", help="the initial state")
    story.add_argument("--when", required=True, metavar="ACTION", help="the action")
    story.add_argument("--then", required=True, metavar="STATE", help="the expected state")
    task = new_command(kinds, "task", "a deliverable of a work item, with its output")
    task.add_argument("title", metavar="TITLE", help="a verb, the artifact and its target state")
    task.add_argument(
        "--parent", required=True, metavar="ID", help="the work item it is written for"
    )
    task.add_argument("--output", required=True, metavar="TEXT", help="the expected output")
    upkeep = new_command(
        kinds, "upkeep", "work that keeps a behavior, with its one Given / When / Then"
    )
    upkeep.add_argument("title", metavar="TITLE", help="what is true once it is completed")
    upkeep.add_argument("--given", required=True, metavar="STATE", help="the initial state")
    upkeep.add_argument("--when", required=True, metavar="ACTION", help="the action that runs")
    upkeep.add_argument("--then", required=True, metavar="STATE", help="what still holds")
    bug = new_command(
        kinds, "bug", "a behavior that fails, with what is observed and what is expected"
    )
    bug.add_argument("title", metavar="TITLE", help="what is true once the Bug is completed")
    bug.add_argument("--observed", required=True, metavar="TEXT", help="what happens")
    bug.add_argument("--expected", required=True, metavar="TEXT", help="what we wish to see")
    spike = new_command(kinds, "spike", "a question to answer, with its hypothesis")
    spike.add_argument("title", metavar="TITLE", help="what is settled once it is completed")
    spike.add_argument("--hypothesis", required=True, metavar="TEXT", help="a yes/no question")
    for kind in (story, upkeep, bug, spike):
        kind.add_argument(
            "--parent", metavar="ID", help="the Feature it is under; it stands alone without one"
        )
        kind.add_argument(
            "--depends-on",
            action="append",
            metavar="ID",
            help="a work item it waits for, which must be completed before it starts; once per id",
        )
        kind.add_argument(
            "--filed-during",
            metavar="ID",
            help="the work item it was found during; it does not change after the add",
        )
        kind.add_argument(
            "--amends",
            metavar="ID",
            help="the completed work item whose landed behavior it changes; once, at the add",
        )
    feature = new_command(
        kinds, "feature", "a bigger outcome that groups work items, with its criteria"
    )
    feature.add_argument("title", metavar="TITLE", help="what is true once it is completed")
    feature.add_argument(
        "--criterion",
        required=True,
        action="append",
        metavar="TEXT",
        help="what the user experiences; give it once per criterion",
    )
    term = new_command(kinds, "term", "a word of the project, with what it means")
    term.add_argument("name", metavar="NAME", help="lowercase words joined by -; it is its id")
    term.add_argument("--means", required=True, metavar="TEXT", help="what the term means")
    made = {
        "story": story,
        "task": task,
        "upkeep": upkeep,
        "bug": bug,
        "spike": spike,
        "feature": feature,
    }
    for kind in (story, upkeep, bug, spike, feature):
        kind.add_argument(
            "--about", action="append", metavar="TERM", help="a term it is about; once per term"
        )
    for kind in made.values():
        kind.add_argument("--description", default="", metavar="TEXT", help="free text, optional")
    return {**made, "term": term}
