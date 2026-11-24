"""The criterion of S-0145: a started or blocked work item or Feature is amended with its deviation.

The part is rewritten and one deviation line is kept in the same write; without the text the amend
is refused. Run end to end on a record in a temporary directory, through the file adapters of the
package.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_STORY = ["add", "story", "a title", *CRITERION, "--description", "why"]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_UNDER = [*ADD_STORY[:3], *CRITERION, "--parent", "F-0001"]
BLOCK_STORY = ["block", "S-0001", "--reason", "a reason", "--waiting-on", "the sponsor"]
BLOCK_FEATURE = ["block", "F-0001", "--reason", "a reason", "--waiting-on", "the sponsor"]
COMPLETE = [
    ["start", "T-0001"],
    ["complete", "T-0001", "--commit", "abc1234"],
    ["complete", "S-0001", "--commit", "abc1234"],
]
STORY_STARTED = (ADD_STORY, ADD_TASK, ["start", "S-0001"])
STORY_BLOCKED = (*STORY_STARTED, BLOCK_STORY)
FEATURE_STARTED = (ADD_FEATURE, ADD_UNDER, ADD_TASK, ["start", "F-0001"])
FEATURE_BLOCKED = (*FEATURE_STARTED, BLOCK_FEATURE)
D = "the then is narrowed to one kind"
NEEDED = "{} is started: amend it with --deviation TEXT, what changes in what it was agreed to do"
IN_BACKLOG = (
    "{} is in Backlog: it has no agreed plan to deviate from -- amend it without --deviation"
)
BACKLOG_ALONE = (
    "{} is started: its complexity, its parent and what it depends on are amended in Backlog alone"
)
TASK_ONLY = "T-0001 takes no --deviation: a Task keeps no knowledge line"
KNOWLEDGE = f"Knowledge (1)\n  deviation  2026-01-01  {D}\n"
AMEND_STORY = ["amend", "S-0001"]
AMEND_THEN = [*AMEND_STORY, "--then", "a new state"]
AMEND_FEATURE = ["amend", "F-0001"]
AMEND_TITLE = [*AMEND_FEATURE, "--title", "another title"]


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


def refusal(outcome: Outcome) -> tuple[int, list[str]]:
    """The exit status of a run and the last line of its error output."""
    return outcome.status, outcome.err.splitlines()[-1:]


def refused(status_line: str) -> tuple[int, list[str]]:
    """What a run refused with that line leaves."""
    return 2, [f"fgraph: error: {status_line}"]


class TestAStartedStoryAmendedWithItsDeviation:
    @pytest.fixture
    def amended(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *STORY_STARTED, [*AMEND_THEN, "--deviation", D])

    def test_amend_exits_with_zero_and_names_the_story(self, amended: Outcome) -> None:
        assert (amended.status, amended.out) == (0, "amended S-0001\n")

    def test_show_lists_the_new_then_in_progress(self, amended: Outcome, tmp_path: Path) -> None:
        lines = fgraph(["show", "S-0001"], tmp_path).out.splitlines()
        assert [line for line in lines if line.startswith(("  bucket", "  then"))] == [
            "  bucket       InProgress",
            "  then         a new state",
        ]

    def test_show_ends_with_the_deviation(self, amended: Outcome, tmp_path: Path) -> None:
        assert fgraph(["show", "S-0001"], tmp_path).out.endswith(KNOWLEDGE)


@pytest.mark.parametrize(
    ("option", "text", "line"),
    [
        ("--title", "another title", "S-0001  another title"),
        ("--description", "why not", "  description  why not"),
        ("--given", "a new state", "  given        a new state"),
        ("--when", "a new action", "  when         a new action"),
    ],
    ids=["title", "description", "given", "when"],
)
def test_each_part_of_a_started_story_is_rewritten_with_its_deviation(
    option: str, text: str, line: str, tmp_path: Path
) -> None:
    amend = [*AMEND_STORY, option, text, "--deviation", D]
    assert line in runs(tmp_path, *STORY_STARTED, amend, ["show", "S-0001"]).out.splitlines()


def test_a_blocked_story_is_amended_with_its_deviation(tmp_path: Path) -> None:
    outcome = runs(tmp_path, *STORY_BLOCKED, [*AMEND_THEN, "--deviation", D])
    assert (outcome.status, outcome.out) == (0, "amended S-0001\n")


@pytest.mark.parametrize("setup", [STORY_STARTED, STORY_BLOCKED], ids=["started", "blocked"])
def test_an_amend_without_a_deviation_of_a_story_is_refused(
    setup: tuple[list[str], ...], tmp_path: Path
) -> None:
    assert refusal(runs(tmp_path, *setup, AMEND_THEN)) == refused(NEEDED.format("S-0001"))


@pytest.mark.parametrize(
    "option",
    [["--complexity", "high"], ["--parent", "none"], ["--depends-on", "S-0002"]],
    ids=["complexity", "parent", "depends-on"],
)
def test_a_started_story_keeps_its_complexity_its_parent_and_its_terms_with_a_deviation(
    option: list[str], tmp_path: Path
) -> None:
    amend = [*AMEND_STORY, *option, "--deviation", D]
    outcome = runs(tmp_path, *STORY_STARTED, ADD_STORY, amend)
    assert refusal(outcome) == refused(BACKLOG_ALONE.format("S-0001"))


def test_a_deviation_alone_amends_no_part_of_a_started_story(tmp_path: Path) -> None:
    outcome = runs(tmp_path, *STORY_STARTED, [*AMEND_STORY, "--deviation", D])
    assert refusal(outcome) == refused("amend rewrites no part of S-0001: name one")


def test_a_blank_deviation_of_a_started_story_is_refused(tmp_path: Path) -> None:
    outcome = runs(tmp_path, *STORY_STARTED, [*AMEND_THEN, "--deviation", " "])
    assert refusal(outcome) == refused("text is empty")


def test_a_story_in_backlog_takes_no_deviation(tmp_path: Path) -> None:
    outcome = runs(tmp_path, ADD_STORY, ADD_TASK, [*AMEND_THEN, "--deviation", D])
    assert refusal(outcome) == refused(IN_BACKLOG.format("S-0001"))


def test_a_completed_story_is_refused_with_a_deviation(tmp_path: Path) -> None:
    outcome = runs(tmp_path, *STORY_STARTED, *COMPLETE, [*AMEND_THEN, "--deviation", D])
    assert refusal(outcome) == refused("S-0001 is completed already")


def test_a_task_takes_no_deviation(tmp_path: Path) -> None:
    amend = ["amend", "T-0001", "--title", "x", "--deviation", D]
    outcome = runs(tmp_path, ADD_STORY, ADD_TASK, amend)
    assert refusal(outcome) == refused(TASK_ONLY)


class TestAStartedFeatureAmendedWithItsDeviation:
    @pytest.fixture
    def amended(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *FEATURE_STARTED, [*AMEND_TITLE, "--deviation", D])

    def test_amend_exits_with_zero_and_names_the_feature(self, amended: Outcome) -> None:
        assert (amended.status, amended.out) == (0, "amended F-0001\n")

    def test_show_starts_with_the_new_title_in_progress(
        self, amended: Outcome, tmp_path: Path
    ) -> None:
        shown = fgraph(["show", "F-0001"], tmp_path).out.splitlines()
        assert shown[:2] == ["F-0001  another title", "  bucket       InProgress"]

    def test_show_ends_with_the_deviation(self, amended: Outcome, tmp_path: Path) -> None:
        assert fgraph(["show", "F-0001"], tmp_path).out.endswith(KNOWLEDGE)


def test_the_criteria_given_replace_those_of_a_started_feature(tmp_path: Path) -> None:
    amend = [*AMEND_FEATURE, "--criterion", "a new one", "--deviation", D]
    shown = runs(tmp_path, *FEATURE_STARTED, amend, ["show", "F-0001"]).out
    assert "Criteria (1)\n  a new one\n" in shown


def test_a_blocked_feature_is_amended_with_its_deviation(tmp_path: Path) -> None:
    outcome = runs(tmp_path, *FEATURE_BLOCKED, [*AMEND_TITLE, "--deviation", D])
    assert (outcome.status, outcome.out) == (0, "amended F-0001\n")


@pytest.mark.parametrize("setup", [FEATURE_STARTED, FEATURE_BLOCKED], ids=["started", "blocked"])
def test_an_amend_without_a_deviation_of_a_feature_is_refused(
    setup: tuple[list[str], ...], tmp_path: Path
) -> None:
    assert refusal(runs(tmp_path, *setup, AMEND_TITLE)) == refused(NEEDED.format("F-0001"))


def test_a_feature_in_backlog_takes_no_deviation(tmp_path: Path) -> None:
    outcome = runs(tmp_path, ADD_FEATURE, [*AMEND_TITLE, "--deviation", D])
    assert refusal(outcome) == refused(IN_BACKLOG.format("F-0001"))


def test_a_completed_feature_is_refused_with_a_deviation(tmp_path: Path) -> None:
    outcome = runs(tmp_path, *FEATURE_STARTED, *COMPLETE, [*AMEND_TITLE, "--deviation", D])
    assert refusal(outcome) == refused("F-0001 is completed already")


@pytest.mark.parametrize(
    ("setup", "amend"),
    [(STORY_STARTED, AMEND_THEN), (FEATURE_STARTED, AMEND_TITLE)],
    ids=["a-story", "a-feature"],
)
def test_an_amend_refused_without_the_text_leaves_the_item_as_it_was(
    setup: tuple[list[str], ...], amend: list[str], tmp_path: Path
) -> None:
    show = ["show", amend[1]]
    before = runs(tmp_path, *setup, show).out
    assert runs(tmp_path, amend, show).out == before
