"""The criterion of S-0073: fgraph about lists the links of a work item, each under its relation.

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
GATE = ["add", "term", "gate", "--means", "a check before a landing"]
FEATURE = ["add", "feature", "a feature title", "--criterion", "a developer sees it"]
FIRST = ["add", "story", "the first title", *CRITERION]
STORY = [
    *("add", "story", "the story title", *CRITERION),
    *("--parent", "F-0001", "--depends-on", "S-0001", "--about", "gate"),
]
NOTE = ["note", "S-0002", "--finding", "a thing learned"]


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


class TestAStoryWithAFeatureADependencyATermAndAKnowledgeLine:
    @pytest.fixture
    def about(self, tmp_path: Path) -> Outcome:
        for argv in (GATE, FEATURE, FIRST, STORY, NOTE):
            fgraph(argv, tmp_path)
        return fgraph(["about", "S-0002"], tmp_path)

    def test_about_exits_with_zero(self, about: Outcome) -> None:
        assert about.status == 0

    def test_about_lists_the_feature_of_the_story(self, about: Outcome) -> None:
        assert "feature (1)\n    F-0001  Backlog  a feature title\n" in about.out

    def test_about_lists_the_work_item_it_depends_on(self, about: Outcome) -> None:
        assert "depends on (1)\n    S-0001  Backlog  the first title\n" in about.out

    def test_about_lists_its_term(self, about: Outcome) -> None:
        assert "terms (1)\n    gate  a check before a landing\n" in about.out

    def test_about_lists_its_knowledge_line(self, about: Outcome) -> None:
        assert "knowledge (1)\n    finding  2026-01-01  a thing learned\n" in about.out
