"""The criterion of B-0021: fgraph graph prints each Task node with its state.

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
ADD_STORY = ["add", "story", "a title", *CRITERION]
ADD_TASKS = [
    ["add", "task", f"task {number}", "--parent", "S-0001", "--output", "an output"]
    for number in range(4)
]
BLOCK = ["block", "T-0002", "--reason", "the review is not back", "--waiting-on", "the reviewer"]
# T-0001 stays in Backlog, T-0002 is blocked, T-0003 started, T-0004 completed.
MOVES = [
    ["start", "S-0001"],
    ["start", "T-0002"],
    BLOCK,
    ["start", "T-0004"],
    ["complete", "T-0004", "--commit", "abc1234"],
    ["start", "T-0003"],
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


RED = pytest.mark.xfail(strict=True, reason="B-0021: a Task node prints bucket null, with no state")


class TestAStoryHoldingATaskInBacklogABlockedOneAStartedOneAndACompletedOne:
    @pytest.fixture
    def graph(self, tmp_path: Path) -> Outcome:
        for argv in (ADD_STORY, *ADD_TASKS, *MOVES):
            fgraph(argv, tmp_path)
        return fgraph(["graph"], tmp_path)

    def nodes(self, graph: Outcome) -> dict[str, dict[str, str | None]]:
        return {node["id"]: node for node in json.loads(graph.out)["nodes"]}

    def state_of(self, graph: Outcome, task: str) -> tuple[str | None, str | None]:
        node = self.nodes(graph)[task]
        return node["bucket"], node.get("state")

    def test_graph_exits_with_zero(self, graph: Outcome) -> None:
        assert graph.status == 0

    @RED
    def test_the_task_in_backlog_is_in_backlog(self, graph: Outcome) -> None:
        assert self.state_of(graph, "T-0001") == ("Backlog", "backlog")

    @RED
    def test_the_blocked_task_is_in_progress_as_blocked(self, graph: Outcome) -> None:
        assert self.state_of(graph, "T-0002") == ("InProgress", "blocked")

    @RED
    def test_the_started_task_is_in_progress_as_started(self, graph: Outcome) -> None:
        assert self.state_of(graph, "T-0003") == ("InProgress", "started")

    @RED
    def test_the_completed_task_is_completed(self, graph: Outcome) -> None:
        assert self.state_of(graph, "T-0004") == ("Completed", "completed")
