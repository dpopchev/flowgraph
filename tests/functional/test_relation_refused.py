"""The criterion of S-0078: a record whose relation names nothing is refused when it is read.

A file of the record edited by hand or merged to name an id that is not in the record makes
`fgraph status` exit with 2 and one line naming the file and the id, never a Python traceback.
Run end to end on a record in a temporary directory, through the file adapters of the package.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
FIRST = ["add", "story", "the first title", *CRITERION]
SECOND = ["add", "story", "the second title", *CRITERION, "--depends-on", "S-0001"]


def fgraph(argv: list[str], cwd: Path) -> tuple[int, str]:
    """Run the command in cwd, whose record is `.fgraph/`: its exit status and error output."""
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


@pytest.mark.xfail(strict=True, reason="S-0078: the relations are not checked at the read yet")
def test_status_of_a_depends_on_that_names_no_work_item_exits_with_two_and_names_file_and_id(
    tmp_path: Path,
) -> None:
    for argv in (FIRST, SECOND):
        fgraph(argv, tmp_path)
    path = tmp_path / ".fgraph" / "items" / "S-0002.toml"
    path.write_text(path.read_text(encoding="utf-8").replace("S-0001", "S-0099"), encoding="utf-8")
    status, err = fgraph(["status"], tmp_path)
    named = f"fgraph: error: {path}: depends on names S-0099, which is not in the record\n"
    assert (status, err.splitlines()[-1:]) == (2, [named.strip()])
