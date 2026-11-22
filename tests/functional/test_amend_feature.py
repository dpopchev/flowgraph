"""The criterion of amending a Feature in Backlog: `fgraph show` of it lists the new title.

Every other part is listed as it was. Run end to end on a record in a temporary directory,
through the file adapters of the package.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
AMEND = ["amend", "F-0001"]
AMEND_TITLE = [*AMEND, "--title", "another title"]
SHOW = ["show", "F-0001"]
NO_FEATURE_YET = "S-0057: fgraph amend takes no Feature yet"


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


def runs(cwd: Path, *argvs: Sequence[str]) -> Outcome:
    """Run each command in cwd in turn; the outcome of the last."""
    outcomes = [fgraph(argv, cwd) for argv in argvs]
    return outcomes[-1]


class TestAFeatureInBacklogAmendedWithANewTitle:
    @pytest.fixture
    def amended(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, ADD_FEATURE, AMEND_TITLE)

    @pytest.mark.xfail(strict=True, reason=NO_FEATURE_YET)
    def test_amend_exits_with_zero(self, amended: Outcome) -> None:
        assert amended.status == 0

    @pytest.mark.xfail(strict=True, reason=NO_FEATURE_YET)
    def test_show_lists_the_new_title_and_every_other_part_as_it_was(
        self, amended: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(SHOW, tmp_path).out == (
            "F-0001  another title\n"
            "  bucket       Backlog\n"
            "Criteria (1)\n"
            "  a criterion\n"
            "Work items (0)\n"
        )
