"""The criterion of S-0077: fgraph graph --format json prints the nodes and edges of the record.

Run end to end on a record in a temporary directory, through the file adapters of the package.
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
FEATURE = ["add", "feature", "a feature title", "--criterion", "a developer sees it"]
FIRST = ["add", "story", "the first title", *CRITERION]
SECOND = [
    *("add", "story", "the second title", *CRITERION),
    *("--parent", "F-0001", "--depends-on", "S-0001", "--about", "gate"),
]
TASK = ["add", "task", "a task title", "--parent", "S-0002", "--output", "an output"]
TERMS = [
    ["add", "term", "gate", "--means", "a check before a landing"],
    ["add", "term", "check", "--means", "a thing that is run"],
    ["relate", "gate", "is-a", "check"],
]
NOTE = ["note", "S-0002", "--finding", "a thing learned", "--about", "gate"]


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


class TestARecordWithAFeatureAWorkItemATaskTwoTermsAndADependency:
    @pytest.fixture
    def graph(self, tmp_path: Path) -> Outcome:
        for argv in (*TERMS, FEATURE, FIRST, SECOND, TASK, NOTE):
            fgraph(argv, tmp_path)
        return fgraph(["graph", "--format", "json"], tmp_path)

    def test_graph_exits_with_zero(self, graph: Outcome) -> None:
        assert graph.status == 0

    def test_graph_prints_every_node_with_its_kind(self, graph: Outcome) -> None:
        nodes = json.loads(graph.out)["nodes"]
        assert [(node["id"], node["kind"]) for node in nodes] == [
            ("F-0001", "feature"),
            ("S-0001", "story"),
            ("S-0002", "story"),
            ("T-0001", "task"),
            ("check", "term"),
            ("gate", "term"),
        ]

    def test_graph_prints_every_edge_with_its_kind_and_its_two_ends(self, graph: Outcome) -> None:
        edges = json.loads(graph.out)["edges"]
        assert [(edge["kind"], edge["from"], edge["to"]) for edge in edges] == [
            ("under", "S-0002", "F-0001"),
            ("task of", "T-0001", "S-0002"),
            ("depends on", "S-0002", "S-0001"),
            ("is a", "gate", "check"),
            ("about", "S-0002", "gate"),
        ]

    def test_graph_prints_the_knowledge_lines_apart(self, graph: Outcome) -> None:
        lines = json.loads(graph.out)["knowledge"]
        assert [(line["item"], line["kind"], line["text"], line["about"]) for line in lines] == [
            ("S-0002", "finding", "a thing learned", ["gate"])
        ]

    def test_graph_prints_the_bucket_of_a_work_item(self, graph: Outcome) -> None:
        nodes = json.loads(graph.out)["nodes"]
        assert [node["bucket"] for node in nodes if node["id"] == "S-0002"] == ["Backlog"]

    def test_graph_prints_the_same_bytes_twice(self, graph: Outcome, tmp_path: Path) -> None:
        assert fgraph(["graph"], tmp_path).out == graph.out
