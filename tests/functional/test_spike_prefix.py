"""The criterion of the prefix of a Spike id: `fgraph status` lists a Spike added as `Q-0001`.

Q stands for question. Run end to end on a record in a temporary directory, through the file
adapters of the package.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
ADD_SPIKE = [
    *("add", "spike", "a spike title"),
    *("--hypothesis", "Can one file per item hold the record?"),
]
SPIKE_FILE = Path(".fgraph") / "items" / "Q-0001.toml"


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


class TestASpikeAddedToARecordWithNoItems:
    @pytest.fixture
    def added(self, tmp_path: Path) -> Outcome:
        return fgraph(ADD_SPIKE, tmp_path)

    def test_add_names_the_spike_by_its_q_id(self, added: Outcome) -> None:
        assert added.out == "added Q-0001\n"

    def test_status_lists_it_as_q_0001_under_backlog(self, added: Outcome, tmp_path: Path) -> None:
        assert fgraph(["status"], tmp_path).out == (
            "Backlog (1)\n> Q-0001  []  a spike title\nInProgress (0)\nCompleted (0)\n"
        )

    def test_the_spike_is_kept_in_the_file_of_its_q_id(
        self, added: Outcome, tmp_path: Path
    ) -> None:
        assert (tmp_path / SPIKE_FILE).is_file()
