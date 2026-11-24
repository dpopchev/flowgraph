"""The criterion of B-0035: two fgraph add run at one time on one record get an id each.

Run end to end through `run` on a record in a temporary directory, the development off and no git.
The second command runs inside the first, after the first has read the ids taken and before it
writes: two writes at one time, the same on every run.
"""

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run
from flowgraph.record.store import OpenStore, Store

pytestmark = pytest.mark.functional

START = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
XFAIL = pytest.mark.xfail(strict=True, reason="B-0035: two writes at one time are given one id")


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path, open_store: OpenStore = open_files) -> Outcome:
    """Run the command at START in cwd, whose record is `.fgraph/`, on the store given."""
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
    @XFAIL
    def test_the_two_outputs_are_not_the_same_line(self, raced: Raced) -> None:
        assert raced.outer.out != raced.inner.out

    @XFAIL
    def test_every_add_that_printed_added_is_listed_after(self, raced: Raced) -> None:
        assert added(raced.outer) + added(raced.inner) == raced.listed


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
