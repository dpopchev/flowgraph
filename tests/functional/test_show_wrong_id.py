"""The criterion of fgraph show given a wrong id: it names every kind it takes, the Feature too.

`fgraph show` takes the id of a Story, an Upkeep, a Bug, a Spike or a Feature; a Feature id below
1 is refused as a Feature id. Run end to end on a record in a temporary directory, through the
file adapters of the package.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def refusal(text: str, cwd: Path) -> tuple[int, list[str]]:
    """The exit status of fgraph show of that text in cwd, and the last line of its error output."""
    (cwd / ".fgraph").mkdir(exist_ok=True)
    err: list[str] = []
    status = run(
        ["show", text],
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
    "text", ["X-0001", "T-0001", "S-0000"], ids=["no-kind", "task", "below-one"]
)
def test_show_of_no_id_it_takes_exits_with_two_and_names_every_kind_and_the_feature(
    text: str, tmp_path: Path
) -> None:
    named = f"fgraph: error: '{text}' is no Story, Upkeep, Bug, Spike or Feature id"
    assert refusal(text, tmp_path) == (2, [named])


def test_show_of_a_feature_id_below_one_exits_with_two_and_says_a_feature_id_counts_from_one(
    tmp_path: Path,
) -> None:
    named = "fgraph: error: a Feature id counts from 1: 0 is below 1"
    assert refusal("F-0000", tmp_path) == (2, [named])
