"""The criterion of the record lookup: `fgraph` names its record, or fails naming the flag."""

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from flowgraph.cli import run

pytestmark = pytest.mark.functional

CWD = Path("/work")


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], *existing: str) -> Outcome:
    """Run the command in CWD, where only the named entries are directories."""
    dirs: Collection[Path] = {CWD / name for name in existing}
    out: list[str] = []
    err: list[str] = []
    status = run(argv, CWD, lambda path: path in dirs, out.append, err.append)
    return Outcome(status, "".join(out), "".join(err))


class TestWithTheDotDirectory:
    @pytest.fixture
    def outcome(self) -> Outcome:
        return fgraph([], ".fgraph", "fgraph")

    def test_exits_with_zero(self, outcome: Outcome) -> None:
        assert outcome.status == 0

    def test_shows_the_help_menu(self, outcome: Outcome) -> None:
        assert outcome.out.startswith("usage: fgraph ")

    def test_names_the_dot_directory(self, outcome: Outcome) -> None:
        assert outcome.out.endswith("record: /work/.fgraph\n")


class TestWithThePlainDirectory:
    def test_names_the_plain_directory(self) -> None:
        assert fgraph([], "fgraph").out.endswith("record: /work/fgraph\n")


class TestWithTheDirectoryGiven:
    def test_names_the_directory_given(self) -> None:
        assert fgraph(["--dir", "/work/other"], ".fgraph", "other").out.endswith(
            "record: /work/other\n"
        )


class TestWithoutARecord:
    @pytest.fixture
    def outcome(self) -> Outcome:
        return fgraph([])

    def test_exits_with_two(self, outcome: Outcome) -> None:
        assert outcome.status == 2

    def test_names_both_directories_and_the_flag(self, outcome: Outcome) -> None:
        assert outcome.err.endswith(
            "fgraph: error: no .fgraph/ or fgraph/ in /work -- pass --dir PATH\n"
        )

    def test_writes_no_output(self, outcome: Outcome) -> None:
        assert outcome.out == ""


class TestWithAGivenPathThatIsNoDirectory:
    @pytest.fixture
    def outcome(self) -> Outcome:
        return fgraph(["--dir", "/work/missing"], ".fgraph")

    def test_exits_with_two(self, outcome: Outcome) -> None:
        assert outcome.status == 2

    def test_names_the_path_given(self, outcome: Outcome) -> None:
        assert outcome.err.endswith("fgraph: error: --dir /work/missing is no directory\n")
