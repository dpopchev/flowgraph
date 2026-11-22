"""The criterion of putting a work item under a Feature: `fgraph show` of it lists the Story.

A Story standing alone is put under a Feature by `fgraph amend --parent`, both in Backlog. Run
end to end on a record in a temporary directory, through the file adapters of the package.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_ALONE = ["add", "story", "a title", *CRITERION]
PUT_UNDER = ["amend", "S-0001", "--parent", "F-0001"]
NO_PARENT_YET = "S-0059: fgraph amend takes no --parent yet"


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


class TestAStoryStandingAlonePutUnderAFeatureBothInBacklog:
    @pytest.fixture
    def put_under(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, ADD_FEATURE, ADD_ALONE, PUT_UNDER)

    @pytest.mark.xfail(strict=True, reason=NO_PARENT_YET)
    def test_amend_exits_with_zero(self, put_under: Outcome) -> None:
        assert put_under.status == 0

    @pytest.mark.xfail(strict=True, reason=NO_PARENT_YET)
    def test_show_of_the_feature_lists_the_story(self, put_under: Outcome, tmp_path: Path) -> None:
        assert fgraph(["show", "F-0001"], tmp_path).out == (
            "F-0001  a feature title\n"
            "  bucket       Backlog\n"
            "Criteria (1)\n"
            "  a criterion\n"
            "Work items (1)\n"
            "  S-0001  a title  Backlog\n"
        )
