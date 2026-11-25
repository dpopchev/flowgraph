"""The criterion of S-0118: fgraph reads an id in any case, without its dash and leading zeros.

On a record holding F-0015, `fgraph show` of f15, f-15, F15 and f-0015 each shows F-0015, and a
text that names no item is refused as before, echoed as typed. Run end to end on a record in a
temporary directory, through the file adapters of the package.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
ADD_FEATURE = [
    *("add", "feature", "a feature title"),
    *("--criterion", "a developer sees every work item by bucket"),
]
SPELLINGS = ["f15", "f-15", "F15", "f-0015"]


def fgraph(argv: list[str], cwd: Path) -> tuple[int, str, str]:
    """Run the command in cwd, whose record is `.fgraph/`: its exit status, output and errors."""
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
    return status, "".join(out), "".join(err)


@pytest.fixture
def record(tmp_path: Path) -> Path:
    """A record in a temporary directory that holds the Features F-0001 to F-0015."""
    for _ in range(15):
        fgraph(ADD_FEATURE, tmp_path)
    return tmp_path


def refusal(text: str, cwd: Path) -> tuple[int, list[str]]:
    """The exit status of fgraph show of that text, and the last line of its error output."""
    status, _, err = fgraph(["show", text], cwd)
    return status, err.splitlines()[-1:]


@pytest.mark.parametrize("text", SPELLINGS)
def test_show_of_a_spelling_of_f_0015_exits_with_zero(text: str, record: Path) -> None:
    assert fgraph(["show", text], record)[0] == 0


@pytest.mark.parametrize("text", SPELLINGS)
def test_show_of_a_spelling_of_f_0015_shows_f_0015(text: str, record: Path) -> None:
    assert fgraph(["show", text], record)[1].splitlines()[0] == "F-0015  a feature title"


def test_show_of_f99_is_refused_as_f_minus_99_is(record: Path) -> None:
    named = "fgraph: error: no Feature F-0099 in the record"
    assert refusal("f99", record) == (2, [named])


def test_show_of_x15_is_refused_as_a_term_missing_from_the_record(record: Path) -> None:
    assert refusal("x15", record) == (2, ["fgraph: error: no term 'x15' in the record"])


@pytest.mark.parametrize("text", ["sp-15", "f-0"])
def test_show_of_a_text_that_is_no_id_is_refused_echoed_as_typed(text: str, record: Path) -> None:
    named = (
        f"fgraph: error: '{text}' is no Story, Upkeep, Bug, Spike or Feature id"
        " nor the name of a term"
    )
    assert refusal(text, record) == (2, [named])
