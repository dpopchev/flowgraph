"""The criterion of a file of the record that holds no item: refused as every other refusal is.

A file of a work item, of a Feature or the queue that holds none of them makes `fgraph status`
exit with 2 and one line naming the file and why, never a Python traceback (B-0019). Run end to
end on a record in a temporary directory, through the file adapters of the package.
"""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
NO_TOML = "state = [\n"


def why() -> str:
    """What the TOML parser says of the text that is no TOML."""
    try:
        tomllib.loads(NO_TOML)
    except tomllib.TOMLDecodeError as error:
        return str(error)
    raise AssertionError(f"{NO_TOML!r} is TOML")


def refusal(cwd: Path) -> tuple[int, list[str]]:
    """The exit status of fgraph status in cwd, and the last line of its error output."""
    err: list[str] = []
    status = run(
        ["status"],
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
    ("name", "kind"),
    [("items/S-0001.toml", "Story"), ("items/F-0001.toml", "Feature"), ("queue.toml", "queue")],
    ids=["work-item", "feature", "queue"],
)
def test_status_of_a_file_that_holds_no_item_exits_with_two_and_names_the_file_and_why(
    name: str, kind: str, tmp_path: Path
) -> None:
    path = tmp_path / ".fgraph" / name
    path.parent.mkdir(parents=True)
    path.write_text(NO_TOML, encoding="utf-8")
    named = f"fgraph: error: {path} holds no {kind}: {why()}"
    assert refusal(tmp_path) == (2, [named])
