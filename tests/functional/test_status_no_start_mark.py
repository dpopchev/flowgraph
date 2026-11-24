"""The criterion of S-0152: `fgraph status` marks no line of the Backlog as able to start.

A line of the Backlog that can start begins with two spaces, like any unmarked line; its `[N T]`
or `[]` tells a planned line from one that is not. The marks `@`, `~`, `!` and `=>` stay, the
more-line keeps its count and `can_start` of the JSON its ids. Run end to end on a record in a
temporary directory, through the file adapters of the package; the development off with no git,
or on with a real git repository whose identity comes from the environment.
"""

import json
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from flowgraph.cli import open_files, open_git, read_config, run

pytestmark = pytest.mark.functional

XFAIL = pytest.mark.xfail(strict=True, reason="S-0152: the line that can start is marked =")

START = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
BLOCK = ["block", "S-0004", "--reason", "no key", "--waiting-on", "developer"]
THREE_AT_ONCE = "[development]\nenabled = true\nparallel = 3\n"
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}


def story(number: int) -> list[str]:
    """The command that adds the Story of that number."""
    return ["add", "story", f"title {number}", *CRITERION]


def task(parent: str) -> list[str]:
    """The command that adds a Task under that parent."""
    return ["add", "task", "a task title", "--parent", parent, "--output", "an output"]


def checked(parent: str) -> list[str]:
    """The command that adds a Task with a check, as the development on takes it."""
    return [*task(parent), "--check", "make test"]


MARKED = [
    *(story(number) for number in range(1, 6)),
    *(task(f"S-000{story}") for story in (3, 4, 5)),
    ["amend", "S-0002", "--depends-on", "S-0001"],
    ["start", "S-0003"],
    ["start", "T-0001"],
    ["complete", "T-0001", "--commit", "abc1231"],
    ["start", "S-0004"],
    BLOCK,
    ["start", "S-0005"],
    ["start", "T-0003"],
]
WITH_TASK = [story(1), task("S-0001")]
WITH_CHECKED_TASK = [story(1), checked("S-0001")]
NO_TASK = [story(1)]
THREE = [*(story(number) for number in range(1, 4)), *(checked(f"S-000{n}") for n in range(1, 4))]
FEATURE_IN_BACKLOG = [
    ["add", "feature", "a feature title", "--criterion", "a developer sees it"],
    [*story(1), "--parent", "F-0001"],
    task("S-0001"),
]
STARTED_FEATURE = [
    ["add", "feature", "a feature title", "--criterion", "a developer sees it"],
    *([*story(number), "--parent", "F-0001"] for number in range(1, 3)),
    *(checked(f"S-000{number}") for number in range(1, 3)),
    ["start", "F-0001"],
]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path, at: datetime) -> Outcome:
    """Run the command at that time in cwd, whose record is `.fgraph/`, on the files of it."""
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
        now=lambda: at,
    )
    return Outcome(status, "".join(out), "".join(err))


def after(cwd: Path, argvs: Sequence[Sequence[str]], last: Sequence[str]) -> Outcome:
    """Run each command in cwd a second after the one before, then the last; its outcome."""
    for seconds, argv in enumerate(argvs):
        fgraph(argv, cwd, START + timedelta(seconds=seconds))
    return fgraph(last, cwd, START + timedelta(seconds=len(argvs)))


def git(cwd: Path, *args: str) -> None:
    """Run the git command in cwd; fails the test on a non-zero exit."""
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def after_on(cwd: Path, argvs: Sequence[Sequence[str]], last: Sequence[str]) -> Outcome:
    """Like `after`, on a real git repository in cwd with the development on, parallel 3."""
    git(cwd, "init", "--quiet", "--initial-branch", "main")
    (cwd / ".fgraph").mkdir()
    (cwd / ".fgraph" / "config.toml").write_text(THREE_AT_ONCE, encoding="utf-8")
    git(cwd, "add", ".fgraph/config.toml")
    git(cwd, "commit", "--quiet", "--message", "chore: start three work items at once")
    outcome = Outcome(0, "", "")
    for argv in [*argvs, last]:
        out: list[str] = []
        err: list[str] = []
        status = run(
            argv,
            cwd,
            Path.is_dir,
            out.append,
            err.append,
            open_store=open_files,
            now=lambda: START,
            open_git=open_git,
            load_config=read_config,
        )
        outcome = Outcome(status, "".join(out), "".join(err))
    return outcome


@pytest.fixture(autouse=True)
def environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The identity of every commit from the environment, and no git config of the machine."""
    for name, value in IDENTITY.items():
        monkeypatch.setenv(name, value)
    empty = tmp_path / "gitconfig"
    empty.touch()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def line_of(out: str, item: str) -> str:
    """The line of the output that names the id."""
    return next(line for line in out.splitlines() if item in line)


class TestAStoryThatCanStartWithTheDevelopmentOn:
    @pytest.fixture
    def listed(self, tmp_path: Path) -> Outcome:
        return after_on(tmp_path, WITH_CHECKED_TASK, ["status", "--backlog"])

    @XFAIL
    def test_its_line_begins_with_two_spaces_and_its_id(self, listed: Outcome) -> None:
        assert line_of(listed.out, "S-0001").startswith("  S-0001")


class TestAStoryWithNoTask:
    @pytest.fixture
    def listed(self, tmp_path: Path) -> Outcome:
        return after(tmp_path, NO_TASK, ["status", "--backlog"])

    @XFAIL
    def test_its_line_begins_with_two_spaces_and_its_id(self, listed: Outcome) -> None:
        assert line_of(listed.out, "S-0001").startswith("  S-0001")


class TestAFeatureInBacklog:
    @pytest.fixture
    def listed(self, tmp_path: Path) -> Outcome:
        return after(tmp_path, FEATURE_IN_BACKLOG, ["status", "--backlog"])

    @XFAIL
    def test_its_line_begins_with_two_spaces_and_its_id(self, listed: Outcome) -> None:
        assert line_of(listed.out, "F-0001").startswith("  F-0001")


class TestAWorkItemInBacklogUnderAStartedFeature:
    @pytest.fixture
    def listed(self, tmp_path: Path) -> Outcome:
        return after_on(tmp_path, STARTED_FEATURE, ["status"])

    @XFAIL
    def test_its_line_is_two_columns_in_and_begins_with_two_spaces(self, listed: Outcome) -> None:
        assert line_of(listed.out, "S-0002").startswith("    S-0002")


class TestWatchOfAStoryThatCanStart:
    @pytest.fixture
    def watched(self, tmp_path: Path) -> Outcome:
        return after(tmp_path, WITH_TASK, ["watch", "--backlog", "--count", "1"])

    @XFAIL
    def test_its_line_begins_with_two_spaces_and_its_id(self, watched: Outcome) -> None:
        assert line_of(watched.out, "S-0001").startswith("  S-0001")


class TestTheMarksThatStay:
    @pytest.fixture
    def listed(self, tmp_path: Path) -> Outcome:
        return after(tmp_path, MARKED, ["status", "--backlog"])

    def test_the_line_that_waits_keeps_a_tilde(self, listed: Outcome) -> None:
        assert line_of(listed.out, "S-0002").startswith("~ S-0002")

    def test_the_blocked_line_keeps_an_exclamation_mark(self, listed: Outcome) -> None:
        assert line_of(listed.out, "S-0004").startswith("! S-0004")

    def test_the_line_ready_for_review_keeps_an_at_sign(self, listed: Outcome) -> None:
        assert line_of(listed.out, "S-0003").startswith("@ S-0003")

    def test_the_task_being_worked_keeps_an_arrow(self, listed: Outcome) -> None:
        assert line_of(listed.out, "T-0003") == "    => T-0003  a task title"


class TestTheMoreLineAndTheJson:
    def test_the_more_line_still_counts_what_can_start(self, tmp_path: Path) -> None:
        listed = after_on(tmp_path, THREE, ["status"])
        assert listed.out.splitlines()[2] == "  ... 2 more, 2 can start"

    def test_can_start_of_the_json_names_the_ids_that_can_start(self, tmp_path: Path) -> None:
        listed = after(tmp_path, WITH_TASK, ["status", "--format", "json"])
        document: dict[str, Any] = json.loads(listed.out)
        assert document["can_start"] == ["S-0001"]
