"""The kinds fgraph note takes and what it refuses: exit 2, one line on stderr and nothing written.

It takes exactly one of --finding, --decision, --deviation and --progress. Run end to end on a
record in a temporary directory, through the file adapters of the package.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
ADD_STORY = ["add", "story", "a title", "--given", "a", "--when", "b", "--then", "c"]
NONE_GIVEN = "one of the arguments --finding --decision --deviation --progress is required"
ITEM = Path(".fgraph") / "items" / "S-0001.toml"


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
        now=lambda: NOW,
        open_git=lambda _: None,
    )
    return Outcome(status, "".join(out), "".join(err))


@pytest.fixture
def record(tmp_path: Path) -> Path:
    """A record holding the Story S-0001, in backlog."""
    assert fgraph(ADD_STORY, tmp_path).status == 0
    return tmp_path


def test_note_without_a_kind_exits_with_two_naming_the_four(
    record: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exited:
        fgraph(["note", "S-0001"], record)
    error = capsys.readouterr().err.splitlines()[-1]
    assert (exited.value.code, error) == (2, f"fgraph note: error: {NONE_GIVEN}")


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (
            ["note", "S-0001", "--finding", "a", "--decision", "b"],
            "argument --decision: not allowed with argument --finding",
        ),
        (
            ["note", "S-0001", "--finding", "a", "--deviation", "b"],
            "argument --deviation: not allowed with argument --finding",
        ),
        (
            ["note", "S-0001", "--decision", "a", "--deviation", "b"],
            "argument --deviation: not allowed with argument --decision",
        ),
    ],
    ids=["finding-decision", "finding-deviation", "decision-deviation"],
)
def test_note_with_two_kinds_exits_with_two_naming_the_second_and_the_first(
    record: Path, capsys: pytest.CaptureFixture[str], argv: list[str], message: str
) -> None:
    with pytest.raises(SystemExit) as exited:
        fgraph(argv, record)
    error = capsys.readouterr().err.splitlines()[-1]
    assert (exited.value.code, error) == (2, f"fgraph note: error: {message}")


def test_a_note_with_two_kinds_writes_nothing(
    record: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = (record / ITEM).read_bytes()
    with pytest.raises(SystemExit):
        fgraph(["note", "S-0001", "--finding", "a", "--decision", "b"], record)
    capsys.readouterr()
    assert (record / ITEM).read_bytes() == before
