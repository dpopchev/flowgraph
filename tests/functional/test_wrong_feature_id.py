"""The criterion of a command that takes a Feature given a Feature id below 1: it is refused as one.

`fgraph start`, `fgraph complete`, `fgraph amend` and `fgraph remove` take a Feature, so `F-0000`
is refused as `fgraph show` refuses it (tests/functional/test_show_wrong_id.py), not as the id of
no work item. Run end to end on a record in a temporary directory, through the file adapters of
the package.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
REFUSAL = "fgraph: error: a Feature id counts from 1: 0 is below 1"


def refusal(argv: list[str], cwd: Path) -> tuple[int, list[str]]:
    """The exit status of fgraph run with argv in cwd, and the last line of its error output."""
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
    return status, "".join(err).splitlines()[-1:]


@pytest.mark.parametrize(
    "argv",
    [
        ["start", "F-0000"],
        ["complete", "F-0000"],
        ["amend", "F-0000", "--title", "a title"],
        ["remove", "F-0000", "--reason", "a reason"],
    ],
    ids=["start", "complete", "amend", "remove"],
)
def test_a_command_given_a_feature_id_below_one_exits_with_two_and_says_it_counts_from_one(
    argv: list[str], tmp_path: Path
) -> None:
    assert refusal(argv, tmp_path) == (2, [REFUSAL])
