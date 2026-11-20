"""The criterion of the help menu: `fgraph --help` and `fgraph -h` print it, no record needed."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import run

pytestmark = pytest.mark.functional


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status and everything it wrote."""

    status: int
    text: str


@pytest.fixture(params=[["--help"], ["-h"]], ids=["--help", "-h"])
def outcome(request: pytest.FixtureRequest) -> Outcome:
    written: list[str] = []
    status = run(
        request.param,
        Path("/work"),
        lambda _: False,
        written.append,
        written.append,
        read_story_rows=lambda _: [],
        write_story=lambda _record, _story: None,
        now=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    )
    return Outcome(status, "".join(written))


class TestHelpMenu:
    def test_exits_with_zero(self, outcome: Outcome) -> None:
        assert outcome.status == 0

    def test_opens_with_the_usage_of_the_command(self, outcome: Outcome) -> None:
        assert outcome.text.startswith("usage: fgraph ")

    def test_says_what_the_command_is_for(self, outcome: Outcome) -> None:
        assert "keeps the record of a project's work" in outcome.text

    def test_lists_the_help_option(self, outcome: Outcome) -> None:
        assert "-h, --help" in outcome.text

    def test_lists_the_dir_option(self, outcome: Outcome) -> None:
        assert "-d, --dir PATH" in outcome.text
