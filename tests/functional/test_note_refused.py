"""The refusals of noting a finding: exit 2 and nothing written, as for any command."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
NOT_AN_ITEM = "'T-0001' is no Story, Upkeep, Bug or Spike id"
ADD_STORY = [
    *("add", "story", "a title"),
    *("--given", "a state", "--when", "an action", "--then", "another"),
]


def fgraph(argv: list[str], cwd: Path) -> tuple[int, str]:
    """Run the command in cwd, whose record is `.fgraph/`: its exit status and its error output."""
    (cwd / ".fgraph").mkdir(exist_ok=True)
    err: list[str] = []
    status = run(
        argv,
        cwd,
        Path.is_dir,
        lambda _: None,
        err.append,
        open_store=open_files,
        open_git=lambda _: None,
        now=lambda: NOW,
    )
    return status, "".join(err)


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (
            ["note", "T-0001", "--finding", "a text"],
            "'T-0001' is no Story, Upkeep, Bug or Spike id",
        ),
        (["note", "S-0002", "--finding", "a text"], "no Story S-0002 in the record"),
        (["note", "S-0001", "--finding", " "], "text is empty"),
    ],
    ids=["a-task", "a-wrong-id", "a-blank-text"],
)
def test_the_refused_note_names_why_and_writes_nothing(
    tmp_path: Path, argv: list[str], message: str
) -> None:
    fgraph(ADD_STORY, tmp_path)
    status, err = fgraph(argv, tmp_path)
    assert (status, err.endswith(f"fgraph: error: {message}\n")) == (2, True)
