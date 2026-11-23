"""The criterion of S-0112: a work item carries its complexity, listed by show and in the JSON.

Run end to end on a record in a temporary directory, through the file adapters of the package.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD = ["add", "story", "a title", *CRITERION]
ADD_HIGH = [*ADD, "--complexity", "high"]
ADD_HUGE = [*ADD, "--complexity", "huge"]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
START = ["start", "S-0001"]
AMEND_HIGH = ["amend", "S-0001", "--complexity", "high"]
AMEND_HUGE = ["amend", "S-0001", "--complexity", "huge"]
SHOW = ["show", "S-0001"]
STATUS = ["status", "--format", "json"]
LINE = "  complexity   high\n"
HUGE = "fgraph: error: --complexity 'huge' is none of low, medium, high, nothing written"
STARTED = "fgraph: error: S-0001 is started already"

red = pytest.mark.xfail(strict=True, reason="S-0112: complexity is not carried yet")


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path) -> Outcome:
    """Run the command in cwd, whose record is `.fgraph/`, on the files of that record."""
    (cwd / ".fgraph").mkdir(exist_ok=True)
    out: list[str] = []
    err: list[str] = []
    try:
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
    except SystemExit as refused:  # argparse refuses an option it does not know, before the run
        status = int(str(refused.code))
    return Outcome(status, "".join(out), "".join(err))


def runs(cwd: Path, *argvs: Sequence[str]) -> Outcome:
    """Run each command in cwd in turn; the outcome of the last."""
    outcomes = [fgraph(argv, cwd) for argv in argvs]
    return outcomes[-1]


def complexity(cwd: Path) -> Any:
    """The complexity of S-0001 in the JSON of status, indexed so that its absence raises."""
    document = json.loads(fgraph(STATUS, cwd).out)
    found = next(i for b in document["buckets"] for i in b["items"] if i["id"] == "S-0001")
    return found["complexity"]


class TestAStoryAddedWithComplexityHigh:
    @pytest.fixture
    def added(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, ADD_HIGH)

    @red
    def test_add_exits_with_zero(self, added: Outcome) -> None:
        assert added.status == 0

    @red
    def test_show_lists_the_complexity(self, added: Outcome, tmp_path: Path) -> None:
        assert LINE in fgraph(SHOW, tmp_path).out

    @red
    def test_status_carries_the_complexity_in_json(self, added: Outcome, tmp_path: Path) -> None:
        assert complexity(tmp_path) == "high"


class TestAStoryAmendedWithComplexityHighInBacklog:
    @pytest.fixture
    def amended(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, ADD, AMEND_HIGH)

    @red
    def test_amend_exits_with_zero(self, amended: Outcome) -> None:
        assert amended.status == 0

    @red
    def test_show_lists_the_complexity(self, amended: Outcome, tmp_path: Path) -> None:
        assert LINE in fgraph(SHOW, tmp_path).out

    @red
    def test_status_carries_the_complexity_in_json(self, amended: Outcome, tmp_path: Path) -> None:
        assert complexity(tmp_path) == "high"


class TestAStoryGivenNoComplexity:
    @pytest.fixture
    def added(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, ADD)

    def test_show_lists_no_complexity(self, added: Outcome, tmp_path: Path) -> None:
        assert "complexity" not in fgraph(SHOW, tmp_path).out

    @red
    def test_status_carries_null_in_json(self, added: Outcome, tmp_path: Path) -> None:
        assert complexity(tmp_path) is None


class TestAStartedStoryGivenComplexityHigh:
    @pytest.fixture
    def started(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, ADD_HIGH, ADD_TASK, START)

    @red
    def test_show_keeps_the_complexity(self, started: Outcome, tmp_path: Path) -> None:
        assert LINE in fgraph(SHOW, tmp_path).out

    @red
    def test_status_keeps_the_complexity_in_json(self, started: Outcome, tmp_path: Path) -> None:
        assert complexity(tmp_path) == "high"


class TestAStartedStoryAmendedWithComplexity:
    @pytest.fixture
    def refused(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, ADD, ADD_TASK, START, AMEND_HIGH)

    def test_amend_exits_with_two(self, refused: Outcome) -> None:
        assert refused.status == 2

    @red
    def test_amend_says_the_story_is_started_already(self, refused: Outcome) -> None:
        assert refused.err.splitlines()[-1] == STARTED


class TestAStoryAddedWithAComplexityThatIsNoneOfThree:
    @pytest.fixture
    def refused(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, ADD_HUGE)

    def test_add_exits_with_two(self, refused: Outcome) -> None:
        assert refused.status == 2

    @red
    def test_add_names_the_three_words(self, refused: Outcome) -> None:
        assert refused.err.splitlines()[-1] == HUGE

    def test_add_writes_no_item_file(self, refused: Outcome, tmp_path: Path) -> None:
        assert list((tmp_path / ".fgraph").glob("**/*.toml")) == []


class TestAStoryAmendedWithAComplexityThatIsNoneOfThree:
    @pytest.fixture
    def refused(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, ADD, AMEND_HUGE)

    def test_amend_exits_with_two(self, refused: Outcome) -> None:
        assert refused.status == 2

    @red
    def test_amend_names_the_three_words(self, refused: Outcome) -> None:
        assert refused.err.splitlines()[-1] == HUGE

    def test_amend_leaves_no_complexity_line(self, refused: Outcome, tmp_path: Path) -> None:
        assert "complexity" not in fgraph(SHOW, tmp_path).out
