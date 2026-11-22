"""The criterion of S-0065: `fgraph knowledge --kind decision` lists every decision of the record.

Run end to end on a record in a temporary directory, through the file adapters of the package.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOT_YET = pytest.mark.xfail(strict=True, reason="S-0065: fgraph has no knowledge command yet")

# Each command with the day of January 2026 it is run on: the lines are noted on different days.
SCRIPT = [
    (1, ["add", "story", "a title", "--given", "a", "--when", "b", "--then", "c"]),
    (1, ["add", "spike", "a spike title", "--hypothesis", "Can one file hold it?"]),
    (1, ["add", "task", "a task title", "--parent", "Q-0001", "--output", "an output"]),
    (2, ["note", "S-0001", "--finding", "the store is plain files"]),
    (3, ["note", "S-0001", "--decision", "keep one store"]),
    (4, ["add", "feature", "a feature title", "--criterion", "a developer lists the record"]),
    (4, ["note", "F-0001", "--decision", "ship in two steps"]),
    (5, ["start", "Q-0001"]),
    (5, ["start", "T-0001"]),
    (5, ["complete", "T-0001", "--commit", "abc1234"]),
    (5, ["complete", "Q-0001", "--commit", "def5678", "--decision", "yes: one file per item"]),
    (6, ["note", "S-0001", "--deviation", "a task was dropped"]),
]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: list[str], cwd: Path, day: int) -> Outcome:
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
        now=lambda: datetime(2026, 1, day, tzinfo=UTC),
    )
    return Outcome(status, "".join(out), "".join(err))


@pytest.fixture
def listed(tmp_path: Path) -> Outcome:
    for day, argv in SCRIPT:
        fgraph(argv, tmp_path, day)
    return fgraph(["knowledge", "--kind", "decision"], tmp_path, 7)


class TestARecordWithKnowledgeOnSeveralItemsAndACompletedSpike:
    @NOT_YET
    def test_knowledge_of_the_decisions_exits_with_zero(self, listed: Outcome) -> None:
        assert listed.status == 0

    @NOT_YET
    def test_knowledge_of_the_decisions_lists_every_one_newest_first_with_its_item(
        self, listed: Outcome
    ) -> None:
        assert listed.out == (
            "2026-01-05  decision  Q-0001  yes: one file per item\n"
            "2026-01-04  decision  F-0001  ship in two steps\n"
            "2026-01-03  decision  S-0001  keep one store\n"
        )
