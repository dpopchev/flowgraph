"""The criterion of S-0074: fgraph about a term lists what is about the terms under it, marked.

Run end to end on a record in a temporary directory, through the file adapters of the package.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
STORY = ["add", "story", "the story title", *CRITERION]
STEPS = [
    ["add", "term", "gate", "--means", "a check before a landing"],
    ["add", "term", "lane", "--means", "a gate of one work item"],
    ["relate", "lane", "part-of", "gate"],
    [*STORY, "--about", "lane"],
    ["note", "S-0001", "--finding", "a thing learned about the whole", "--about", "gate"],
    ["note", "S-0001", "--finding", "a thing learned about the part", "--about", "lane"],
]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: list[str], cwd: Path) -> Outcome:
    """Run the command in cwd, whose record is `.fgraph/`, on the files of that record."""
    (cwd / ".fgraph").mkdir(exist_ok=True)
    out: list[str] = []
    err: list[str] = []
    status = run(
        argv,
        cwd,
        Path.is_dir,
        out.append,
        err.append,
        open_store=open_files,
        open_git=lambda _: None,
        now=lambda: NOW,
    )
    return Outcome(status, "".join(out), "".join(err))


class TestATermWithAPartAboutWhichALineWasNoted:
    @pytest.fixture
    def about(self, tmp_path: Path) -> Outcome:
        for argv in STEPS:
            fgraph(argv, tmp_path)
        return fgraph(["about", "gate"], tmp_path)

    def test_about_exits_with_zero(self, about: Outcome) -> None:
        assert about.status == 0

    def test_about_lists_the_line_about_the_whole_unmarked(self, about: Outcome) -> None:
        assert "S-0001  finding  2026-01-01  a thing learned about the whole\n" in about.out

    def test_about_lists_the_line_about_the_part_marked_with_the_part(self, about: Outcome) -> None:
        assert "a thing learned about the part  (via lane)\n" in about.out

    def test_about_lists_the_story_about_the_part_marked_with_the_part(
        self, about: Outcome
    ) -> None:
        assert "  items  S-0001  (via lane)\n" in about.out

    def test_about_lists_the_meaning_of_the_term(self, about: Outcome) -> None:
        assert "  means  a check before a landing\n" in about.out

    def test_about_lists_the_part_of_the_term_in_its_relations(self, about: Outcome) -> None:
        assert "  parts  lane\n" in about.out


class TestAWordThatIsNoIdAndNoTerm:
    @pytest.fixture
    def about(self, tmp_path: Path) -> Outcome:
        return fgraph(["about", "nope"], tmp_path)

    def test_about_exits_with_two(self, about: Outcome) -> None:
        assert about.status == 2

    def test_about_names_the_ids_and_the_term_it_is_neither(self, about: Outcome) -> None:
        said = "'nope' is no Story, Upkeep, Bug, Spike or Feature id and no term in the record\n"
        assert about.err.endswith(said)
