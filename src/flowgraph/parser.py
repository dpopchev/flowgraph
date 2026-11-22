"""The arguments of the `fgraph` command line: its commands, their options and their help.

Every command prints its own help. A command asked for its help is given without its required
arguments, so the arguments are read for the command they name before argparse parses them.
"""

import argparse
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

DESCRIPTION = "flowgraph keeps the record of a project's work."

# The options that ask for help.
HELP = ("-h", "--help")

# The options of the command line that take the record directory as their value.
DIR = ("-d", "--dir")

# The items status lists under one heading, unless every one is asked for.
TOP = 5

# The seconds watch waits between two frames, unless others are given.
EVERY = 5

# The path of a command among the commands: `()` the command line, `("add", "story")` a kind,
# `("config", "set")` an action.
CommandPath = tuple[str, ...]


class Commands(Protocol):
    """The commands a parser holds, as argparse makes them: each is added as a parser of its own."""

    def add_parser(
        self, name: str, *, help: str, add_help: bool, color: bool
    ) -> argparse.ArgumentParser: ...


@dataclass(frozen=True)
class CommandLine:
    """The parser of the command line, and the parser of each command under its path."""

    parser: argparse.ArgumentParser
    commands: Mapping[CommandPath, argparse.ArgumentParser]


def _command(parsers: Commands, name: str, summary: str) -> argparse.ArgumentParser:
    """A command of that name under the parsers, with its help option.

    The help option only marks the call: `run` writes the help through its own writer, where
    argparse's built-in one prints and exits. Color is off so the help is the same text on
    every stream.
    """
    made = parsers.add_parser(name, help=summary, add_help=False, color=False)
    made.add_argument(*HELP, action="store_true", help="show the help of this command and exit")
    return made


def _add_kinds(kinds: Commands) -> dict[str, argparse.ArgumentParser]:
    """The parser of each kind of item `fgraph add` takes, under its name."""
    story = _command(kinds, "story", "new behavior, with its one Given / When / Then")
    story.add_argument("title", metavar="TITLE", help="what is true once the Story is completed")
    story.add_argument("--given", required=True, metavar="STATE", help="the initial state")
    story.add_argument("--when", required=True, metavar="ACTION", help="the action")
    story.add_argument("--then", required=True, metavar="STATE", help="the expected state")
    task = _command(kinds, "task", "a deliverable of a work item, with its output")
    task.add_argument("title", metavar="TITLE", help="a verb, the artifact and its target state")
    task.add_argument(
        "--parent", required=True, metavar="ID", help="the work item it is written for"
    )
    task.add_argument("--output", required=True, metavar="TEXT", help="the expected output")
    upkeep = _command(
        kinds, "upkeep", "work that keeps a behavior, with its one Given / When / Then"
    )
    upkeep.add_argument("title", metavar="TITLE", help="what is true once it is completed")
    upkeep.add_argument("--given", required=True, metavar="STATE", help="the initial state")
    upkeep.add_argument("--when", required=True, metavar="ACTION", help="the action that runs")
    upkeep.add_argument("--then", required=True, metavar="STATE", help="what still holds")
    bug = _command(
        kinds, "bug", "a behavior that fails, with what is observed and what is expected"
    )
    bug.add_argument("title", metavar="TITLE", help="what is true once the Bug is completed")
    bug.add_argument("--observed", required=True, metavar="TEXT", help="what happens")
    bug.add_argument("--expected", required=True, metavar="TEXT", help="what we wish to see")
    spike = _command(kinds, "spike", "a question to answer, with its hypothesis")
    spike.add_argument("title", metavar="TITLE", help="what is settled once it is completed")
    spike.add_argument("--hypothesis", required=True, metavar="TEXT", help="a yes/no question")
    for kind in (story, upkeep, bug, spike):
        kind.add_argument(
            "--parent", metavar="ID", help="the Feature it is under; it stands alone without one"
        )
    feature = _command(
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
    made = {
        "story": story,
        "task": task,
        "upkeep": upkeep,
        "bug": bug,
        "spike": spike,
        "feature": feature,
    }
    for kind in made.values():
        kind.add_argument("--description", default="", metavar="TEXT", help="free text, optional")
    return made


def _moves(commands: Commands) -> dict[str, argparse.ArgumentParser]:
    """The parser of each command that reads or moves an item of the record, under its name."""
    amend = _command(commands, "amend", "rewrite parts of a work item or a Feature in Backlog")
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
    show = _command(commands, "show", "show a work item with its Tasks, or a Feature")
    show.add_argument("id", metavar="ID", help="the id of the work item or of the Feature")
    start = _command(commands, "start", "start a work item or a Task of it, or a Feature")
    start.add_argument(
        "id", metavar="ID", help="the id of the work item, of the Task or of the Feature"
    )
    start.add_argument(
        "--slug",
        metavar="TEXT",
        help="the words of a work item's branch after its id, instead of its title's first four",
    )
    block = _command(commands, "block", "block a started Task or Feature that cannot go on")
    block.add_argument("id", metavar="ID", help="the id of the Task or of the Feature")
    block.add_argument("--reason", required=True, metavar="TEXT", help="why it cannot go on")
    block.add_argument(
        "--waiting-on", required=True, metavar="TEXT", help="who or what it waits on"
    )
    unblock = _command(commands, "unblock", "take a blocked Task or Feature back to started")
    unblock.add_argument("id", metavar="ID", help="the id of the Task or of the Feature")
    complete = _command(commands, "complete", "complete a work item or a Task of it")
    complete.add_argument("id", metavar="ID", help="the id of the work item or of the Task")
    complete.add_argument(
        "--commit",
        metavar="SHA",
        help="the commit that holds its work: needed with the development on, optional with it off",
    )
    complete.add_argument(
        "--decision", metavar="TEXT", help="what answers the hypothesis, of a Spike"
    )
    land = _command(
        commands, "land", "land a started work item on main: merge its branch and complete it"
    )
    land.add_argument("id", metavar="ID", help="the id of the work item")
    land.add_argument(
        "--message",
        metavar="TEXT",
        help="the message of the commit the landing makes: needed unless it lands by fast-forward",
    )
    land.add_argument("--decision", metavar="TEXT", help="what answers the hypothesis, of a Spike")
    remove = _command(commands, "remove", "remove a work item in Backlog, kept with its reason")
    remove.add_argument("id", metavar="ID", help="the id of the work item")
    remove.add_argument("--reason", required=True, metavar="TEXT", help="why it is removed")
    reorder = _command(commands, "reorder", "put a work item of the Backlog before another")
    reorder.add_argument("id", metavar="ID", help="the id of the work item to move")
    reorder.add_argument(
        "--before", required=True, metavar="ID", help="the work item it is listed right above"
    )
    status = _command(commands, "status", "list the items of the record by bucket")
    status.add_argument(
        "--all",
        action="store_true",
        help=f"list every item, instead of the top {TOP} under each heading",
    )
    watch = _command(commands, "watch", "follow the record live: redraw its status every interval")
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
        "start": start,
        "block": block,
        "unblock": unblock,
        "complete": complete,
        "land": land,
        "remove": remove,
        "reorder": reorder,
        "status": status,
        "watch": watch,
    }


def _config_actions(actions: Commands) -> dict[str, argparse.ArgumentParser]:
    """The parser of each action `fgraph config` takes, under its name."""
    show = _command(actions, "show", "list every key of the configuration with its value")
    set_key = _command(actions, "set", "set one key of the configuration, in its config.toml")
    set_key.add_argument(
        "key", metavar="KEY", help="a key fgraph config show lists, as development.enabled"
    )
    set_key.add_argument("value", metavar="VALUE", help="the value the key takes, as a text")
    return {"show": show, "set": set_key}


def build_command_line() -> CommandLine:
    """The parser of the command line with its help text, and the parser of every command."""
    parser = argparse.ArgumentParser(
        prog="fgraph", description=DESCRIPTION, add_help=False, color=False
    )
    parser.add_argument(*HELP, action="store_true", help="show this help menu and exit")
    parser.add_argument(
        *DIR,
        type=Path,
        metavar="PATH",
        help="the record directory, instead of .fgraph/ or else fgraph/ in this directory",
    )
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")
    add = _command(commands, "add", "add an item to the record")
    kinds = _add_kinds(add.add_subparsers(dest="kind", metavar="KIND", required=True))
    moves = _moves(commands)
    config = _command(commands, "config", "show the configuration of the record, or set a key")
    actions = _config_actions(config.add_subparsers(dest="action", metavar="ACTION", required=True))
    return CommandLine(
        parser,
        {
            (): parser,
            ("add",): add,
            **{("add", name): kind for name, kind in kinds.items()},
            **{(name,): move for name, move in moves.items()},
            ("config",): config,
            **{("config", name): action for name, action in actions.items()},
        },
    )


def command_path(argv: Sequence[str], commands: Collection[CommandPath]) -> CommandPath:
    """The command the arguments name, as its path among the commands.

    The value of the record directory before the command, and every option, is passed over; the
    first word that names no command ends the path, since it is an argument of the command.
    """
    path: CommandPath = ()
    words = iter(argv)
    for word in words:
        if word in DIR and not path:
            next(words, None)
        elif word.startswith("-"):
            continue
        elif (*path, word) in commands:
            path = (*path, word)
        else:
            break
    return path


def help_asked(argv: Sequence[str], command_line: CommandLine) -> str | None:
    """The help the arguments ask for, that of the command they name; None when they ask none."""
    if not any(word in HELP for word in argv):
        return None
    return command_line.commands[command_path(argv, command_line.commands)].format_help()
