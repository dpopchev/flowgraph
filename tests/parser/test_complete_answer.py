"""The arguments of complete and land: `--answer` takes yes or no, beside `--decision`."""

import pytest

from flowgraph.parser import build_command_line

pytestmark = pytest.mark.view

COMMAND_LINE = build_command_line()


@pytest.mark.parametrize("command", ["complete", "land"])
@pytest.mark.parametrize(
    ("answer", "kept"), [([], None), (["--answer", "no"], "no"), (["--answer", "yes"], "yes")]
)
def test_the_command_takes_the_answer_given_or_none(
    command: str, answer: list[str], kept: str | None
) -> None:
    assert COMMAND_LINE.parser.parse_args([command, "Q-0001", *answer]).answer == kept


@pytest.mark.parametrize("command", ["complete", "land"])
def test_the_command_refuses_an_answer_other_than_yes_or_no(
    command: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit):
        COMMAND_LINE.parser.parse_args([command, "Q-0001", "--answer", "maybe"])
    assert "invalid choice: 'maybe' (choose from" in capsys.readouterr().err
