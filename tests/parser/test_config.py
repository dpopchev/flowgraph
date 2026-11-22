"""The arguments of config: it shows the configuration, or sets one key to a value."""

import pytest

from flowgraph.parser import build_command_line

pytestmark = pytest.mark.view

COMMAND_LINE = build_command_line()
PARSER = COMMAND_LINE.parser


def test_config_show_names_its_action() -> None:
    assert PARSER.parse_args(["config", "show"]).action == "show"


def test_config_set_takes_the_key_and_the_text_of_its_value() -> None:
    args = PARSER.parse_args(["config", "set", "development.gate", "make check"])
    assert (args.action, args.key, args.value) == ("set", "development.gate", "make check")


def test_config_set_takes_a_value_below_zero_as_a_text() -> None:
    assert PARSER.parse_args(["config", "set", "development.parallel", "-1"]).value == "-1"


@pytest.mark.parametrize(
    "argv",
    [["config"], ["config", "unset"], ["config", "set"], ["config", "set", "git.commit"]],
    ids=["no-action", "another-action", "no-key", "no-value"],
)
def test_config_without_what_its_action_takes_exits_with_two(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as refused:
        PARSER.parse_args(argv)
    assert refused.value.code == 2


def test_the_help_of_config_set_says_where_its_keys_are_listed() -> None:
    helped = " ".join(COMMAND_LINE.commands["config", "set"].format_help().split())
    assert "KEY a key fgraph config show lists, as development.enabled" in helped
