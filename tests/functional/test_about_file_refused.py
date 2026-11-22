"""A path fgraph about cannot answer for is refused, naming why, and nothing is written.

Run end to end through `run` on a record in a temporary directory.
"""

import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, open_git, run
from flowgraph.commit import OpenGit

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status and its error output."""

    status: int
    err: str


def about(text: str, cwd: Path, git: OpenGit) -> Outcome:
    """Run fgraph about the text in cwd, whose record is `.fgraph/`, inside the git given."""
    (cwd / ".fgraph").mkdir(exist_ok=True)
    err: list[str] = []
    status = run(
        ["about", text],
        cwd,
        Path.is_dir,
        lambda _: None,
        err.append,
        open_store=open_files,
        open_git=git,
        now=lambda: NOW,
    )
    return Outcome(status, "".join(err))


class TestAFileOutsideAGitWorkTree:
    @pytest.fixture
    def refused(self, tmp_path: Path) -> Outcome:
        (tmp_path / "work.txt").write_text("a file\n", encoding="utf-8")
        return about("work.txt", tmp_path, lambda _: None)

    def test_about_exits_with_two(self, refused: Outcome) -> None:
        assert refused.status == 2

    def test_about_says_the_answer_is_read_from_git(self, refused: Outcome) -> None:
        assert "the answer for a file is read from git" in refused.err


class TestAFileOutsideTheWorkTreeOfTheDirectory:
    @pytest.fixture
    def refused(self, tmp_path: Path) -> Outcome:
        (tmp_path / "elsewhere.txt").write_text("a file\n", encoding="utf-8")
        project = tmp_path / "project"
        project.mkdir()
        subprocess.run(["git", "init", "--quiet"], cwd=project, check=True)
        return about("../elsewhere.txt", project, open_git)

    def test_about_exits_with_two(self, refused: Outcome) -> None:
        assert refused.status == 2

    def test_about_says_the_answer_is_read_from_git(self, refused: Outcome) -> None:
        assert "is outside the git work tree" in refused.err


class TestAWordThatIsNoIdNoTermAndNoFile:
    @pytest.fixture
    def refused(self, tmp_path: Path) -> Outcome:
        return about("nope", tmp_path, lambda _: None)

    def test_about_exits_with_two(self, refused: Outcome) -> None:
        assert refused.status == 2

    def test_about_names_the_id_the_term_and_the_file(self, refused: Outcome) -> None:
        said = "'nope' is no Story, Upkeep, Bug, Spike or Feature id, no term in the record"
        assert said + " and no file\n" in refused.err
