"""The criterion of the names of the buckets: fgraph prints them in kebab case, in text and in JSON.

Run end to end on a record in a temporary directory with an item in each bucket, through the
file adapters of the package with no git, each command one second after the one before it.
"""

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

START = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
NAMES = ["backlog", "in-progress", "completed", "removed"]
OLD = re.compile(r"\b(Backlog|InProgress|Completed|Removed)\b")

EACH = [
    ["add", "feature", "a feature title", "--criterion", "a criterion"],
    ["add", "story", "title 1", *CRITERION, "--parent", "F-0001", "--realizes", "1"],
    ["add", "story", "title 2", *CRITERION],
    ["add", "story", "title 3", *CRITERION],
    ["add", "task", "a task title", "--parent", "S-0003", "--output", "an output"],
    ["start", "S-0003"],
    ["start", "T-0001"],
    ["add", "story", "title 4", *CRITERION],
    ["add", "task", "a task title", "--parent", "S-0004", "--output", "an output"],
    ["start", "S-0004"],
    ["start", "T-0002"],
    ["complete", "T-0002", "--commit", "abc1234"],
    ["complete", "S-0004", "--commit", "abc1234"],
    ["amend", "S-0002", "--depends-on", "S-0004"],
    ["add", "story", "title 5", *CRITERION],
    ["remove", "S-0005", "--reason", "filed by mistake"],
]

OUTPUTS = [
    ["status", "--all"],
    ["status", "--all", "--format", "json"],
    ["show", "S-0002"],
    ["show", "S-0003"],
    ["show", "S-0004"],
    ["show", "S-0005"],
    ["show", "F-0001"],
    ["graph"],
    ["graph", "--format", "json"],
    ["brief", "S-0002"],
    ["brief", "S-0002", "--format", "json"],
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


def printed(cwd: Path, argv: Sequence[str]) -> str:
    """The output of the command on the record of an item in each bucket."""
    return after(cwd, EACH, argv).out


class TestStatus:
    def test_the_headings_of_status_are_the_four_names(self, tmp_path: Path) -> None:
        text = printed(tmp_path, ["status", "--all"])
        headings = [
            line.rsplit(" ", 1)[0] for line in text.splitlines() if re.match(r"^\S+ \(\d+\)$", line)
        ]
        assert headings == NAMES

    def test_the_json_of_status_names_the_four_buckets(self, tmp_path: Path) -> None:
        buckets = json.loads(printed(tmp_path, ["status", "--all", "--format", "json"]))["buckets"]
        assert [bucket["name"] for bucket in buckets] == NAMES

    def test_the_json_of_status_keeps_the_state_of_an_item(self, tmp_path: Path) -> None:
        buckets = json.loads(printed(tmp_path, ["status", "--all", "--format", "json"]))["buckets"]
        started = [item for item in buckets[1]["items"] if item["id"] == "S-0003"]
        assert [item["state"] for item in started] == ["started"]


class TestShow:
    @pytest.mark.parametrize(
        ("item", "name"),
        [
            ("S-0002", "backlog"),
            ("S-0003", "in-progress"),
            ("S-0004", "completed"),
            ("S-0005", "removed"),
        ],
    )
    def test_the_second_line_of_a_work_item_is_its_bucket(
        self, tmp_path: Path, item: str, name: str
    ) -> None:
        assert printed(tmp_path, ["show", item]).splitlines()[1] == f"  bucket       {name}"

    def test_a_dependency_is_named_with_its_bucket(self, tmp_path: Path) -> None:
        assert (
            "  depends on   S-0004 (completed)"
            in printed(tmp_path, ["show", "S-0002"]).splitlines()
        )

    def test_a_feature_names_its_bucket(self, tmp_path: Path) -> None:
        assert "  bucket       backlog" in printed(tmp_path, ["show", "F-0001"]).splitlines()

    def test_a_feature_lists_its_work_item_with_its_bucket(self, tmp_path: Path) -> None:
        lines = printed(tmp_path, ["show", "F-0001"]).splitlines()
        assert [line for line in lines if line.startswith("  S-0001")] == [
            "  S-0001  title 1  backlog"
        ]

    def test_a_task_names_its_bucket(self, tmp_path: Path) -> None:
        assert (
            "    bucket           in-progress" in printed(tmp_path, ["show", "S-0003"]).splitlines()
        )


class TestGraphAndBrief:
    def test_the_graph_names_the_bucket_of_each_node(self, tmp_path: Path) -> None:
        nodes = json.loads(printed(tmp_path, ["graph", "--format", "json"]))["nodes"]
        assert {node["id"]: node["bucket"] for node in nodes} == {
            "F-0001": "backlog",
            "S-0001": "backlog",
            "S-0002": "backlog",
            "S-0003": "in-progress",
            "S-0004": "completed",
            "S-0005": "removed",
            "T-0001": "in-progress",
            "T-0002": "completed",
        }

    def test_the_brief_names_its_dependency_as_completed(self, tmp_path: Path) -> None:
        assert (
            "  depends on   S-0004 (completed)"
            in printed(tmp_path, ["brief", "S-0002"]).splitlines()
        )

    def test_the_json_of_the_brief_holds_the_bucket(self, tmp_path: Path) -> None:
        assert '"bucket": "backlog"' in printed(tmp_path, ["brief", "S-0002", "--format", "json"])


class TestNoOldName:
    @pytest.mark.parametrize("argv", OUTPUTS, ids=[" ".join(argv) for argv in OUTPUTS])
    def test_no_output_holds_an_old_name_as_a_word(self, tmp_path: Path, argv: list[str]) -> None:
        assert OLD.findall(printed(tmp_path, argv)) == []


class TestARefusedStart:
    def test_a_task_of_a_work_item_in_backlog_is_refused_in_prose(self, tmp_path: Path) -> None:
        added = [
            *EACH,
            ["add", "task", "another task", "--parent", "S-0002", "--output", "an output"],
        ]
        refused = after(tmp_path, added, ["start", "T-0003"])
        assert (
            refused.err.splitlines()[-1]
            == "fgraph: error: T-0003 cannot start: S-0002 is in Backlog"
        )
