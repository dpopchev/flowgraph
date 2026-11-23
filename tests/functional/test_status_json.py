"""The criterion of S-0087: fgraph status --format json prints the buckets and every item of them.

Run end to end on a record in a temporary directory, through the file adapters of the package.
The record holds an item in every bucket, a blocked Task, a blocked Feature and a Story that
waits for another.
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")


def story(title: str, *more: str) -> list[str]:
    """The command that adds a Story of that title."""
    return ["add", "story", title, *CRITERION, *more]


def task(parent: str) -> list[str]:
    """The command that adds a Task to that work item."""
    return ["add", "task", "a task title", "--parent", parent, "--output", "an output"]


RECORD = [
    ["add", "feature", "a feature title", "--criterion", "a developer sees it"],
    story("the blocked story"),
    task("S-0001"),
    task("S-0001"),
    story("the waiting story", "--depends-on", "S-0001"),
    story("the free story"),
    story("the story of the feature", "--parent", "F-0001"),
    task("S-0004"),
    story("the completed story"),
    task("S-0005"),
    story("the removed story"),
    ["start", "S-0001"],
    ["start", "T-0001"],
    ["block", "T-0001", "--reason", "no key", "--waiting-on", "the developer"],
    ["start", "F-0001"],
    ["block", "F-0001", "--reason", "no budget", "--waiting-on", "the sponsor"],
    ["start", "S-0005"],
    ["start", "T-0004"],
    ["complete", "T-0004", "--commit", "abc1234"],
    ["complete", "S-0005", "--commit", "def5678"],
    ["remove", "S-0006", "--reason", "not wanted"],
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


def bucket(document: dict[str, Any], name: str) -> dict[str, Any]:
    """The bucket of that name of the document."""
    return next(each for each in document["buckets"] if each["name"] == name)


def item(document: dict[str, Any], id_: str) -> dict[str, Any]:
    """The item of that id, found in any bucket of the document."""
    return next(each for b in document["buckets"] for each in b["items"] if each["id"] == id_)


@pytest.fixture
def recorded(tmp_path: Path) -> Path:
    for argv in RECORD:
        assert fgraph(argv, tmp_path).status == 0
    return tmp_path


@pytest.fixture
def printed(recorded: Path) -> Outcome:
    return fgraph(["status", "--format", "json"], recorded)


@pytest.fixture
def document(printed: Outcome) -> dict[str, Any]:
    return json.loads(printed.out)


class TestARecordWithAnItemInEveryBucket:
    def test_status_exits_with_zero(self, printed: Outcome) -> None:
        assert printed.status == 0

    def test_status_prints_the_count_of_each_bucket(self, document: dict[str, Any]) -> None:
        assert [(each["name"], each["count"]) for each in document["buckets"]] == [
            ("Backlog", 2),
            ("InProgress", 2),
            ("Completed", 1),
            ("Removed", 1),
        ]

    def test_status_prints_the_blocked_task_with_its_reason_and_what_it_waits_on(
        self, document: dict[str, Any]
    ) -> None:
        first = item(document, "S-0001")["tasks"][0]
        assert (first["id"], first["state"], first["reason"], first["waiting_on"]) == (
            "T-0001",
            "blocked",
            "no key",
            "the developer",
        )

    def test_status_prints_the_blocked_feature_with_its_reason_and_what_it_waits_on(
        self, document: dict[str, Any]
    ) -> None:
        assert item(document, "F-0001")["block"] == {
            "reason": "no budget",
            "waiting_on": "the sponsor",
        }

    def test_status_prints_the_feature_with_its_work_items(self, document: dict[str, Any]) -> None:
        assert [each["id"] for each in item(document, "F-0001")["work_items"]] == ["S-0004"]

    def test_status_prints_the_id_a_waiting_story_waits_for(self, document: dict[str, Any]) -> None:
        assert item(document, "S-0002")["waits_for"] == ["S-0001"]

    def test_status_prints_the_next_to_start(self, document: dict[str, Any]) -> None:
        assert document["next_to_start"] == "S-0003"

    def test_status_prints_the_reason_of_a_removed_story(self, document: dict[str, Any]) -> None:
        assert bucket(document, "Removed")["items"][0]["reason"] == "not wanted"

    def test_status_prints_the_same_bytes_twice(self, printed: Outcome, recorded: Path) -> None:
        assert fgraph(["status", "--format", "json"], recorded).out == printed.out

    def test_status_prints_the_same_with_all(self, printed: Outcome, recorded: Path) -> None:
        assert fgraph(["status", "--format", "json", "--all"], recorded).out == printed.out

    def test_status_of_the_format_text_prints_what_it_prints_by_default(
        self, recorded: Path
    ) -> None:
        assert (
            fgraph(["status", "--format", "text"], recorded).out == fgraph(["status"], recorded).out
        )

    def test_status_of_a_format_that_is_none_exits_with_two(self, recorded: Path) -> None:
        assert fgraph(["status", "--format", "xml"], recorded).status == 2

    def test_status_of_a_format_that_is_none_names_the_two(self, recorded: Path) -> None:
        assert (
            "--format 'xml' is not text or json"
            in fgraph(["status", "--format", "xml"], recorded).err
        )


FEATURE_RECORD = [
    ["add", "feature", "a feature title", "--criterion", "a developer sees it"],
    story("the completed one", "--parent", "F-0001"),
    story("the started one", "--parent", "F-0001"),
    story("the one in backlog", "--parent", "F-0001"),
    task("S-0001"),
    task("S-0002"),
    ["start", "F-0001"],
    ["start", "T-0001"],
    ["complete", "T-0001", "--commit", "abc1234"],
    ["complete", "S-0001", "--commit", "def5678"],
]


class TestAFeatureWithACompletedAStartedAndABacklogWorkItem:
    @pytest.fixture
    def feature(self, tmp_path: Path) -> dict[str, Any]:
        for argv in FEATURE_RECORD:
            assert fgraph(argv, tmp_path).status == 0
        return item(json.loads(fgraph(["status", "--format", "json"], tmp_path).out), "F-0001")

    def test_status_lists_every_work_item_of_the_feature_with_its_state(
        self, feature: dict[str, Any]
    ) -> None:
        assert [(each["id"], each["state"]) for each in feature["work_items"]] == [
            ("S-0001", "completed"),
            ("S-0002", "started"),
            ("S-0003", "backlog"),
        ]

    def test_status_counts_the_work_items_of_the_feature_as_before(
        self, feature: dict[str, Any]
    ) -> None:
        assert feature["progress"] == {"completed": 1, "total": 3}
