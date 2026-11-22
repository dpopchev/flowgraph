"""The criterion of S-0071: two terms related with part-of are shown, each side by its name.

Run end to end on a record in a temporary directory, through the file adapters of the package.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: list[str], cwd: Path) -> Outcome:
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


class TestTwoTermsRelatedWithPartOf:
    @pytest.fixture
    def related(self, tmp_path: Path) -> Outcome:
        fgraph(["add", "term", "gate", "--means", "a check before a landing"], tmp_path)
        fgraph(["add", "term", "lane", "--means", "one work item in its own worktree"], tmp_path)
        return fgraph(["relate", "gate", "part-of", "lane"], tmp_path)

    def test_relate_exits_with_zero(self, related: Outcome) -> None:
        assert related.status == 0

    def test_show_of_the_first_lists_that_it_is_part_of_the_second(
        self, related: Outcome, tmp_path: Path
    ) -> None:
        assert "  part of  lane\n" in fgraph(["show", "gate"], tmp_path).out

    def test_show_of_the_second_lists_the_first_as_its_part(
        self, related: Outcome, tmp_path: Path
    ) -> None:
        assert "  parts  gate\n" in fgraph(["show", "lane"], tmp_path).out


@pytest.fixture
def terms(tmp_path: Path) -> Path:
    """A record with the terms gate and lane."""
    fgraph(["add", "term", "gate", "--means", "a check before a landing"], tmp_path)
    fgraph(["add", "term", "lane", "--means", "one work item in its own worktree"], tmp_path)
    return tmp_path


@pytest.mark.parametrize(
    ("argv", "said"),
    [
        (["relate", "gate", "owns", "lane"], "'owns' is no kind of relation: is-a or part-of"),
        (["relate", "gate", "part-of", "none"], "no term 'none' in the record"),
        (["relate", "gate", "part-of", "gate"], "gate cannot be part-of itself"),
    ],
    ids=["a-kind-outside-the-set", "a-term-not-in-the-record", "itself"],
)
def test_a_relation_refused_exits_with_two_and_says_why(
    argv: list[str], said: str, terms: Path
) -> None:
    refused = fgraph(argv, terms)
    assert (refused.status, refused.err.splitlines()[-1]) == (2, f"fgraph: error: {said}")


def test_a_relation_kept_already_exits_with_two_and_writes_nothing(terms: Path) -> None:
    fgraph(["relate", "gate", "part-of", "lane"], terms)
    kept = (terms / ".fgraph" / "terms" / "gate.toml").read_text(encoding="utf-8")
    again = fgraph(["relate", "gate", "part-of", "lane"], terms)
    now = (terms / ".fgraph" / "terms" / "gate.toml").read_text(encoding="utf-8")
    assert (again.status, now) == (2, kept)


def test_a_relation_that_closes_a_cycle_exits_with_two_and_writes_nothing(terms: Path) -> None:
    fgraph(["relate", "gate", "part-of", "lane"], terms)
    refused = fgraph(["relate", "lane", "part-of", "gate"], terms)
    assert (
        refused.status,
        "part_of" in (terms / ".fgraph" / "terms" / "lane.toml").read_text(),
    ) == (
        2,
        False,
    )
