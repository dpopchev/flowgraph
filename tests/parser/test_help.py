"""The help of the command line: the command the arguments name, and the help they ask for."""

import pytest

from flowgraph.parser import build_command_line, command_path, help_asked

pytestmark = pytest.mark.view

COMMAND_LINE = build_command_line()


@pytest.mark.parametrize(
    ("argv", "path"),
    [
        ([], ()),
        (["--help"], ()),
        (["start", "--help"], ("start",)),
        (["start", "S-0001"], ("start",)),
        (["add", "story", "--help"], ("add", "story")),
        (["add", "--help"], ("add",)),
        (["--dir", "elsewhere", "start"], ("start",)),
        (["-d", "start", "status"], ("status",)),
        (["start", "--slug", "status"], ("start",)),
        (["config", "show", "--help"], ("config", "show")),
        (["config", "set", "development.gate", "status"], ("config", "set")),
    ],
    ids=[
        "nothing",
        "the-menu",
        "a-command",
        "a-command-with-its-argument",
        "a-kind-under-add",
        "add-alone",
        "after-dir",
        "a-dir-named-as-a-command",
        "an-option-value-named-as-a-command",
        "an-action-under-config",
        "a-value-of-config-set-named-as-a-command",
    ],
)
def test_the_arguments_name_the_command_by_its_path(argv: list[str], path: tuple[str, ...]) -> None:
    assert command_path(argv, COMMAND_LINE.commands) == path


def test_arguments_without_the_help_option_ask_for_no_help() -> None:
    assert help_asked(["start", "S-0001"], COMMAND_LINE) is None


def test_the_help_option_alone_asks_for_the_menu() -> None:
    assert help_asked(["--help"], COMMAND_LINE) == COMMAND_LINE.parser.format_help()


def test_the_help_option_after_a_command_asks_for_the_help_of_that_command() -> None:
    asked = help_asked(["start", "S-0001", "-h"], COMMAND_LINE)
    assert asked == COMMAND_LINE.commands["start",].format_help()


def test_every_command_lists_its_help_option() -> None:
    without = [
        " ".join(path)
        for path, parser in COMMAND_LINE.commands.items()
        if "-h, --help" not in parser.format_help()
    ]
    assert without == []


def test_relate_names_its_two_terms_and_the_two_kinds_in_its_help() -> None:
    helped = COMMAND_LINE.commands["relate",].format_help()
    assert tuple(word for word in ("TERM", "KIND", "is-a", "part-of") if word in helped) == (
        "TERM",
        "KIND",
        "is-a",
        "part-of",
    )


def test_every_command_kind_under_add_and_action_under_config_has_its_help() -> None:
    assert sorted(COMMAND_LINE.commands) == sorted(
        [
            (),
            ("about",),
            ("add",),
            ("add", "bug"),
            ("add", "feature"),
            ("add", "spike"),
            ("add", "story"),
            ("add", "task"),
            ("add", "term"),
            ("add", "upkeep"),
            ("amend",),
            ("block",),
            ("complete",),
            ("config",),
            ("config", "set"),
            ("config", "show"),
            ("config", "unset"),
            ("graph",),
            ("init",),
            ("knowledge",),
            ("land",),
            ("note",),
            ("relate",),
            ("remove",),
            ("reorder",),
            ("show",),
            ("start",),
            ("status",),
            ("terms",),
            ("unblock",),
            ("verify",),
            ("watch",),
        ]
    )
