"""The arguments of the `fgraph` command line: its commands, their options and their help.

Every command prints its own help. A command asked for its help is given without its required
arguments, so the arguments are read for the command they name before argparse parses them.
The commands that read or move an item are built in flowgraph.parser.item_commands; goal is
built in flowgraph.parser.goal and hand in flowgraph.parser.hand.
"""

import argparse
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from flowgraph.parser.add import add_kinds
from flowgraph.parser.base import HELP, Commands, new_command
from flowgraph.parser.goal import goal_command
from flowgraph.parser.hand import hand_command
from flowgraph.parser.item_commands import item_commands

DESCRIPTION = "flowgraph keeps the record of a project's work."

# The options of the command line that take the record directory as their value.
DIR = ("-d", "--dir")

# The path of a command among the commands: `()` the command line, `("add", "story")` a kind,
# `("config", "set")` an action.
CommandPath = tuple[str, ...]


@dataclass(frozen=True)
class CommandLine:
    """The parser of the command line, and the parser of each command under its path."""

    parser: argparse.ArgumentParser
    commands: Mapping[CommandPath, argparse.ArgumentParser]


def _config_actions(actions: Commands) -> dict[str, argparse.ArgumentParser]:
    """The parser of each action `fgraph config` takes, under its name."""
    show = new_command(actions, "show", "list every key of the configuration with its value")
    set_key = new_command(actions, "set", "set one key of the configuration, in its config.toml")
    set_key.add_argument(
        "key", metavar="KEY", help="a key fgraph config show lists, as development.enabled"
    )
    set_key.add_argument("value", metavar="VALUE", help="the value the key takes, as a text")
    unset_key = new_command(
        actions, "unset", "take one key of the configuration back to its default, or none"
    )
    unset_key.add_argument(
        "key", metavar="KEY", help="a key fgraph config show lists, as development.gate"
    )
    return {"show": show, "set": set_key, "unset": unset_key}


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
    init = new_command(
        commands,
        "init",
        "make the record: .fgraph/ in this directory, or in the --dir one, which holds none",
    )
    add = new_command(commands, "add", "add an item to the record")
    kinds = add_kinds(add.add_subparsers(dest="kind", metavar="KIND", required=True))
    moves = item_commands(commands)
    hand = hand_command(commands)
    config = new_command(commands, "config", "show the configuration of the record, or set a key")
    actions = _config_actions(config.add_subparsers(dest="action", metavar="ACTION", required=True))
    goal = goal_command(commands)
    sync = new_command(
        commands, "sync", "merge main into the branch of a started work item, run in its worktree"
    )
    return CommandLine(
        parser,
        {
            (): parser,
            ("init",): init,
            ("add",): add,
            **{("add", name): kind for name, kind in kinds.items()},
            **{(name,): move for name, move in moves.items()},
            ("hand",): hand,
            ("config",): config,
            **{("config", name): action for name, action in actions.items()},
            ("goal",): goal,
            ("sync",): sync,
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
