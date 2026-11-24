"""The criterion of S-0120: a `.board/` of board 1 is archived beside a new record of fgraph.

Given a repository with a `.board/` of board 1 that holds open and closed items, when the developer
starts a record of fgraph in it, then the `.fgraph/` holds the open work alone, the old board stays
whole as an archive nothing writes to, and an item of the old board is found from the new record by
the id it held.

The Decision of S-0120: a pointer, never a read of board 1. `archive.board` names the `.board/`;
`fgraph show` of an id of board 1 says where it is archived and the command that shows it, and no
file of the archive is opened. Run end to end through `run` on the real files in tmp_path.
"""

import subprocess
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, open_git, read_config, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
ADD_STORY = [
    "add",
    "story",
    "Raise the Stories fgraph lists from 0 to 1",
    "--given",
    "a state",
    "--when",
    "an action",
    "--then",
    "another",
]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
SET = ["config", "set", "archive.board", ".board"]
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}
BOARD = {
    "board.toml": "a binding of board 1\n",
    "items/E-007.md": "a closed Epic\n",
    "items/W-123.md": "a closed work item\n",
    "items/W-124.md": "an open work item\n",
    "items/T-456.md": "a closed Task\n",
}
LINE = (
    "fgraph: error: {old} is in the archive of board 1 at {where} -- show it with: "
    "uv run ~/.claude/skills/board/scripts/board.py --root {root} show {old}"
)
NO_ID = "fgraph: error: {!r} is no Story, Upkeep, Bug, Spike or Feature id"


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path, git: bool = False) -> Outcome:
    """Run the command in cwd on its files, on the real git when git is true, else on none."""
    out: list[str] = []
    err: list[str] = []
    status = run(
        argv,
        cwd,
        Path.is_dir,
        out.append,
        err.append,
        open_store=open_files,
        open_git=open_git if git else lambda _: None,
        now=lambda: NOW,
        load_config=read_config,
        make_dir=Path.mkdir,
    )
    return Outcome(status, "".join(out), "".join(err))


def run_git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def last_line(outcome: Outcome) -> str:
    """The last line of the error output."""
    return outcome.err.strip().splitlines()[-1] if outcome.err.strip() else ""


def said(old: str, project: Path) -> str:
    """The line fgraph says for the old id in the project that holds its archive."""
    return LINE.format(old=old, where=project / ".board", root=project)


def board_bytes(project: Path) -> dict[str, bytes]:
    """Every file under .board/ of the project, by its path, with its bytes."""
    root = project / ".board"
    return {
        str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()
    }


@pytest.fixture(autouse=True)
def environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The identity of every commit from the environment, and no git config of the machine."""
    for name, value in IDENTITY.items():
        monkeypatch.setenv(name, value)
    empty = tmp_path / "gitconfig"
    empty.touch()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


@pytest.fixture
def beside(tmp_path: Path) -> Path:
    """A project directory holding the `.board/` of board 1, and no record."""
    project = tmp_path / "project"
    for name, text in BOARD.items():
        path = project / ".board" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return project


@pytest.fixture
def record(beside: Path) -> Path:
    """The project after fgraph init and the pointer set, asserting nothing."""
    fgraph(["init"], beside)
    fgraph(SET, beside)
    return beside


class TestThePointerToTheArchive:
    def test_a_set_of_the_key_says_what_it_set(self, beside: Path) -> None:
        fgraph(["init"], beside)
        outcome = fgraph(SET, beside)
        assert outcome == Outcome(0, 'set archive.board = ".board"\n', "")

    def test_config_show_lists_the_pointer_set(self, record: Path) -> None:
        shown = fgraph(["config", "show"], record)
        assert 'archive.board = ".board"' in shown.out.splitlines()

    def test_config_toml_holds_the_pointer_in_its_table(self, record: Path) -> None:
        held = tomllib.loads((record / ".fgraph" / "config.toml").read_text(encoding="utf-8"))
        assert held == {
            "git": {"commit": True},
            "development": {"enabled": False},
            "archive": {"board": ".board"},
        }

    def test_config_show_lists_no_pointer_as_none_at_the_defaults(self, beside: Path) -> None:
        fgraph(["init"], beside)
        shown = fgraph(["config", "show"], beside)
        assert "archive.board = none" in shown.out.splitlines()


class TestAnOldIdAskedOfARecordThatPointsAtTheArchive:
    @pytest.mark.parametrize(
        ("asked", "old"),
        [
            ("W-123", "W-123"),
            ("E-007", "E-007"),
            ("T-456", "T-456"),
            ("t456", "T-456"),
            ("T-1364", "T-1364"),
            ("w-7", "W-007"),
        ],
    )
    def test_show_names_the_archive_and_the_command_that_shows_it(
        self, record: Path, asked: str, old: str
    ) -> None:
        outcome = fgraph(["show", asked], record)
        assert (outcome.status, outcome.out, last_line(outcome)) == (2, "", said(old, record))

    def test_show_of_a_task_number_names_the_old_task_not_the_one_of_the_record(
        self, record: Path
    ) -> None:
        fgraph(ADD_STORY, record)
        fgraph(ADD_TASK, record)
        outcome = fgraph(["show", "T-1"], record)
        assert (outcome.status, outcome.out, last_line(outcome)) == (2, "", said("T-001", record))


class TestWhatStaysAsItWas:
    def test_status_of_a_record_with_no_item_lists_three_empty_buckets(self, beside: Path) -> None:
        fgraph(["init"], beside)
        shown = fgraph(["status", "--all"], beside)
        assert shown.out == "backlog (0)\nin-progress (0)\ncompleted (0)\n"

    def test_a_story_added_is_the_one_item_of_the_record(self, beside: Path) -> None:
        fgraph(["init"], beside)
        fgraph(ADD_STORY, beside)
        assert sorted(p.name for p in (beside / ".fgraph" / "items").iterdir()) == ["S-0001.toml"]

    def test_with_no_pointer_an_old_work_item_id_is_refused_as_no_id(self, beside: Path) -> None:
        fgraph(["init"], beside)
        outcome = fgraph(["show", "W-123"], beside)
        assert (outcome.status, last_line(outcome)) == (2, NO_ID.format("W-123"))

    def test_with_no_pointer_an_old_task_id_is_refused_as_read(self, beside: Path) -> None:
        fgraph(["init"], beside)
        outcome = fgraph(["show", "T-456"], beside)
        assert (outcome.status, last_line(outcome)) == (2, NO_ID.format("T-0456"))

    @pytest.mark.parametrize("asked", ["X-123", "W-0"])
    def test_an_id_that_board_1_never_held_is_refused_as_no_id(
        self, record: Path, asked: str
    ) -> None:
        outcome = fgraph(["show", asked], record)
        assert last_line(outcome) == NO_ID.format(asked)

    def test_show_of_an_id_of_fgraph_prints_the_item(self, record: Path) -> None:
        fgraph(ADD_STORY, record)
        shown = fgraph(["show", "S-0001"], record)
        assert shown.out.startswith("S-0001")

    def test_with_the_pointer_unset_an_old_id_is_refused_as_no_id(self, record: Path) -> None:
        fgraph(["config", "unset", "archive.board"], record)
        outcome = fgraph(["show", "W-123"], record)
        assert last_line(outcome) == NO_ID.format("W-123")

    def test_every_file_of_the_old_board_keeps_its_bytes(self, beside: Path) -> None:
        before = board_bytes(beside)
        fgraph(["init"], beside)
        fgraph(SET, beside)
        fgraph(ADD_STORY, beside)
        fgraph(["show", "W-123"], beside)
        fgraph(ADD_TASK, beside)
        assert board_bytes(beside) == before

    def test_no_commit_of_fgraph_holds_a_file_of_the_old_board(self, beside: Path) -> None:
        run_git(beside, "init", "--quiet", "--initial-branch", "main")
        run_git(beside, "add", ".board")
        run_git(beside, "commit", "--quiet", "--message", "add the board")
        fgraph(["init"], beside, git=True)
        fgraph(SET, beside, git=True)
        fgraph(ADD_STORY, beside, git=True)
        assert (
            run_git(beside, "status", "--porcelain"),
            run_git(beside, "log", "--format=%s", "--", ".board"),
        ) == ("", "add the board")
