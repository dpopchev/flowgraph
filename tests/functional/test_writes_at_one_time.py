"""The criterion of B-0035: two fgraph add run at one time on one record get an id each.

Run end to end through `run` on a record in a temporary directory, the development off and no git,
each run given the lock of lock_files with a wait that does not wait. The second command runs
inside the first, after the first has read the ids taken and before it writes: two writes at one
time, the same on every run. Then four fgraph add run as real processes on a git repository.
"""

import json
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from functools import partial
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run
from flowgraph.record.lock import lock_files
from flowgraph.record.store import OpenStore, Store

pytestmark = pytest.mark.functional

START = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}
FOUR = range(1, 5)


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path, open_store: OpenStore = open_files) -> Outcome:
    """Run the command at START in cwd, whose record is `.fgraph/`, on the store given, locked."""
    (cwd / ".fgraph").mkdir(exist_ok=True)
    out: list[str] = []
    err: list[str] = []
    status = run(
        argv,
        cwd,
        Path.is_dir,
        out.append,
        err.append,
        open_store=open_store,
        open_git=lambda _: None,
        now=lambda: START,
        lock_record=partial(lock_files, wait=lambda _: None),
    )
    return Outcome(status, "".join(out), "".join(err))


def racing(cwd: Path, inner: Sequence[str], kept: list[Outcome]) -> OpenStore:
    """The store of the record whose first save runs the inner command whole, kept, then saves."""

    def before[Saved](save: Callable[[Saved], None]) -> Callable[[Saved], None]:
        def saved(value: Saved) -> None:
            if not kept:
                kept.append(fgraph(inner, cwd))
            save(value)

        return saved

    def open_store(record: Path) -> Store:
        store = open_files(record)
        features = replace(store.features, save_feature=before(store.features.save_feature))
        return replace(store, save_work_item=before(store.save_work_item), features=features)

    return open_store


def story(title: str) -> list[str]:
    """The command that adds a Story of that title."""
    return ["add", "story", title, *CRITERION]


def feature(title: str) -> list[str]:
    """The command that adds a Feature of that title, with a criterion."""
    return ["add", "feature", title, "--criterion", "a developer sees it"]


def task(title: str) -> list[str]:
    """The command that adds a Task of that title to S-0001."""
    return ["add", "task", title, "--parent", "S-0001", "--output", "an output"]


PAIRS = {
    "story": (story("the first"), story("the second")),
    "feature": (feature("the first"), feature("the second")),
    "task": (task("the first"), task("the second")),
}


def listed(cwd: Path, kind: str) -> int:
    """How many items of that kind the record lists: in the buckets of status, or under S-0001."""
    if kind == "task":
        shown = fgraph(["show", "S-0001"], cwd).out.splitlines()
        return sum(1 for line in shown if line.startswith("  T-"))
    document = json.loads(fgraph(["status", "--format", "json"], cwd).out)
    return sum(len(bucket["items"]) for bucket in document["buckets"])


@dataclass(frozen=True)
class Raced:
    """The two adds run at one time: the outer, the inner and how many items are listed after."""

    outer: Outcome
    inner: Outcome
    listed: int


@pytest.fixture(params=sorted(PAIRS))
def raced(request: pytest.FixtureRequest, tmp_path: Path) -> Raced:
    kind: str = request.param
    if kind == "task":
        fgraph(story("the story"), tmp_path)
    first, second = PAIRS[kind]
    kept: list[Outcome] = []
    outer = fgraph(first, tmp_path, racing(tmp_path, second, kept))
    return Raced(outer, kept[0], listed(tmp_path, kind))


def added(outcome: Outcome) -> int:
    """How many lines of the output of the run start with added."""
    return sum(1 for line in outcome.out.splitlines() if line.startswith("added"))


class TestTwoAddsAtOneTime:
    def test_the_two_outputs_are_not_the_same_line(self, raced: Raced) -> None:
        assert raced.outer.out != raced.inner.out

    def test_every_add_that_printed_added_is_listed_after(self, raced: Raced) -> None:
        assert added(raced.outer) + added(raced.inner) == raced.listed


class TestTwoStoriesAtOneTime:
    @pytest.fixture
    def inner(self, tmp_path: Path) -> Outcome:
        first, second = PAIRS["story"]
        kept: list[Outcome] = []
        fgraph(first, tmp_path, racing(tmp_path, second, kept))
        return kept[0]

    def test_the_second_exits_with_two(self, inner: Outcome) -> None:
        assert inner.status == 2

    def test_the_second_says_the_record_is_being_written(
        self, inner: Outcome, tmp_path: Path
    ) -> None:
        assert inner.err.splitlines()[-1] == (
            f"fgraph: error: {tmp_path / '.fgraph'} is being written by another fgraph: "
            "run the command again"
        )

    def test_the_record_holds_the_first_alone(self, inner: Outcome, tmp_path: Path) -> None:
        assert sorted(each.name for each in (tmp_path / ".fgraph" / "items").iterdir()) == [
            "S-0001.toml"
        ]

    def test_the_story_kept_has_the_title_of_the_first(
        self, inner: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["show", "S-0001"], tmp_path).out.splitlines()[0] == "S-0001  the first"

    def test_an_add_run_after_the_pair_is_given_s_0002(
        self, inner: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(story("the third"), tmp_path).out == "added S-0002\n"


def test_two_adds_one_after_the_other_print_two_ids(tmp_path: Path) -> None:
    outputs = [fgraph(story(title), tmp_path).out for title in ("the first", "the second")]
    assert outputs == ["added S-0001\n", "added S-0002\n"]


class TestStatusWhileAnAddIsMade:
    @pytest.fixture
    def kept(self, tmp_path: Path) -> tuple[Outcome, Outcome]:
        kept: list[Outcome] = []
        outer = fgraph(story("the first"), tmp_path, racing(tmp_path, ["status"], kept))
        return outer, kept[0]

    def test_status_exits_with_zero(self, kept: tuple[Outcome, Outcome]) -> None:
        assert kept[1].status == 0

    def test_the_add_prints_added_s_0001(self, kept: tuple[Outcome, Outcome]) -> None:
        assert kept[0].out == "added S-0001\n"


def git(repository: Path, environment: dict[str, str], *argv: str) -> str:
    """Run git in the repository with that environment; what it printed."""
    done = subprocess.run(
        ["git", *argv], cwd=repository, env=environment, capture_output=True, text=True, check=True
    )
    return done.stdout


@dataclass(frozen=True)
class Processes:
    """Four fgraph add run at one time as processes: the repository, the environment, the runs."""

    repository: Path
    environment: dict[str, str]
    outcomes: list[Outcome]


@pytest.fixture(scope="module")
def processes(tmp_path_factory: pytest.TempPathFactory) -> Processes:
    """Four fgraph add story started together on a git repository with one commit, waited for."""
    repository = tmp_path_factory.mktemp("project")
    empty = repository.parent / "gitconfig"
    empty.touch()
    environment = {
        **os.environ,
        **IDENTITY,
        "GIT_CONFIG_GLOBAL": str(empty),
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    git(repository, environment, "init", "--quiet", "--initial-branch", "main")
    git(repository, environment, "commit", "--quiet", "--allow-empty", "--message", "chore: begin")
    (repository / ".fgraph").mkdir()
    started = [
        subprocess.Popen(
            [sys.executable, "-m", "flowgraph.cli", *story(f"title {number}")],
            cwd=repository,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for number in FOUR
    ]
    return Processes(repository, environment, [finished(each) for each in started])


def finished(process: subprocess.Popen[str]) -> Outcome:
    """What the process left once it has exited."""
    out, err = process.communicate()
    return Outcome(process.returncode, out, err)


class TestFourAddsAsProcesses:
    def test_the_four_are_given_four_ids(self, processes: Processes) -> None:
        assert sorted(each.out for each in processes.outcomes) == [
            f"added S-000{number}\n" for number in FOUR
        ]

    def test_every_one_exits_with_zero(self, processes: Processes) -> None:
        assert [each.status for each in processes.outcomes] == [0, 0, 0, 0]

    def test_the_record_holds_four_files(self, processes: Processes) -> None:
        assert len(list((processes.repository / ".fgraph" / "items").iterdir())) == 4

    def test_git_log_holds_the_four_commits(self, processes: Processes) -> None:
        logged = git(processes.repository, processes.environment, "log", "--format=%s")
        assert sorted(logged.splitlines()[:4]) == [
            f"chore: add S-000{number} in the record" for number in FOUR
        ]

    def test_git_status_is_empty(self, processes: Processes) -> None:
        assert git(processes.repository, processes.environment, "status", "--porcelain") == ""
