"""The criterion of S-0082: `fgraph init` makes the record of a directory that holds none.

Run end to end through `run` on the real files of a directory in tmp_path, outside any git work
tree.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, read_config, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
ADD_STORY = [
    "add",
    "story",
    "Raise the Stories fgraph lists from 0 to 1",
    "--given",
    "a state",
    "--when",
    "an action",
    "--then",
    "another",
]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path) -> Outcome:
    """Run the command in cwd on its files, outside any git work tree."""
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
        load_config=read_config,
        make_dir=Path.mkdir,
    )
    return Outcome(status, "".join(out), "".join(err))


class TestInADirectoryWithNoRecord:
    @pytest.fixture
    def outcome(self, tmp_path: Path) -> Outcome:
        return fgraph(["init"], tmp_path)

    def test_exits_with_zero(self, outcome: Outcome) -> None:
        assert outcome.status == 0

    def test_prints_the_record_it_made(self, outcome: Outcome, tmp_path: Path) -> None:
        assert outcome.out == f"record: {tmp_path / '.fgraph'}\n"

    def test_makes_the_dot_directory(self, outcome: Outcome, tmp_path: Path) -> None:
        assert (tmp_path / ".fgraph").is_dir()


class TestAStoryAddedAfterInit:
    @pytest.fixture
    def added(self, tmp_path: Path) -> Outcome:
        fgraph(["init"], tmp_path)
        return fgraph(ADD_STORY, tmp_path)

    def test_is_added_with_zero(self, added: Outcome) -> None:
        assert added.status == 0

    def test_is_listed_under_backlog_by_status(self, added: Outcome, tmp_path: Path) -> None:
        listed = fgraph(["status"], tmp_path).out
        assert "S-0001" in listed.split("backlog")[-1]


class TestInADirectoryThatHoldsARecord:
    @pytest.fixture
    def kept(self, tmp_path: Path) -> Path:
        fgraph(["init"], tmp_path)
        (tmp_path / ".fgraph" / "config.toml").write_text("[git]\ncommit = false\n")
        return tmp_path

    @pytest.fixture
    def outcome(self, kept: Path) -> Outcome:
        return fgraph(["init"], kept)

    def test_exits_with_two(self, outcome: Outcome) -> None:
        assert outcome.status == 2

    def test_names_the_record_it_holds(self, outcome: Outcome, kept: Path) -> None:
        assert f"{kept / '.fgraph'}" in outcome.err

    def test_writes_nothing(self, outcome: Outcome, kept: Path) -> None:
        assert (kept / ".fgraph" / "config.toml").read_text() == "[git]\ncommit = false\n"
