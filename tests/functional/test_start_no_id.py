"""The criterion of S-0121: fgraph start with no id starts the first Backlog line that can start.

Each test is one fact of a start given no id; the guards pin what a start that names its id does.
Run end to end through `run` on a real git repository in a temporary directory, never a faked
git; the identity of its commits comes from the environment and no git config is read.
"""

import json
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, open_git, read_config, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}
ON = "[development]\nenabled = true\n"
ONE = ON + "parallel = 1\n"
FIRST = "a first title"
SECOND = "a second title"
THIRD = "a third title"
FEATURE = ["add", "feature", "a feature title", "--criterion", "a developer sees it"]
NONE = (
    "fgraph: error: nothing to start: no line of the Backlog can start now, fgraph status marks"
    " none -- fgraph start {} says why its first line cannot"
)
EMPTY = "fgraph: error: nothing to start: the Backlog is empty"
NO_SLUG = "fgraph: error: S-0002 takes no --slug: the development is off"


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path) -> Outcome:
    """Run the command in cwd, whose record is `.fgraph/`, on its files and the real git."""
    (cwd / ".fgraph").mkdir(exist_ok=True)
    out: list[str] = []
    err: list[str] = []
    try:
        status = run(
            argv,
            cwd,
            Path.is_dir,
            out.append,
            err.append,
            open_store=open_files,
            now=lambda: NOW,
            open_git=open_git,
            load_config=read_config,
        )
    except SystemExit as refused:  # argparse refuses a start with two ids before the run
        status = int(str(refused.code))
    return Outcome(status, "".join(out), "".join(err))


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def last(outcome: Outcome) -> list[str]:
    """The last line of the error output, as a list: empty when there is none."""
    return outcome.err.splitlines()[-1:]


def story(title: str, parent: str | None = None) -> list[str]:
    """The command that adds the Story of that title, under the Feature of parent when given."""
    argv = ["add", "story", title, *CRITERION]
    return [*argv, "--parent", parent] if parent else argv


def task(parent: str, checked: bool) -> list[str]:
    """The command that adds a Task to that work item, with a check only when checked."""
    argv = ["add", "task", "a task title", "--parent", parent, "--output", "an output"]
    return [*argv, "--check", "make test"] if checked else argv


def waits(checked: bool) -> list[list[str]]:
    """Two Stories, a Task each; S-0001 waits for S-0002, which waits for nothing."""
    return [
        story(FIRST),
        story(SECOND),
        task("S-0001", checked),
        task("S-0002", checked),
        ["amend", "S-0001", "--depends-on", "S-0002"],
    ]


def free(checked: bool) -> list[list[str]]:
    """The same two Stories, neither waiting for the other."""
    return [story(FIRST), story(SECOND), task("S-0001", checked), task("S-0002", checked)]


def checkout_with(tmp_path: Path, config: str | None, commands: Sequence[Sequence[str]]) -> Path:
    """A git checkout of main in tmp_path / "project", with config.toml when config is given.

    Each command runs in turn and must exit 0; its error output is the message when it does not.
    """
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    if config is not None:
        (path / ".fgraph").mkdir()
        (path / ".fgraph" / "config.toml").write_text(config, encoding="utf-8")
        git(path, "add", ".fgraph/config.toml")
        git(path, "commit", "--quiet", "--message", "chore: turn the development on")
    for argv in commands:
        outcome = fgraph(argv, path)
        assert outcome.status == 0, outcome.err
    return path


@pytest.fixture(autouse=True)
def environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The identity of every commit from the environment, and no git config of the machine."""
    for name, value in IDENTITY.items():
        monkeypatch.setenv(name, value)
    empty = tmp_path / "gitconfig"
    empty.touch()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


# Development off: a record with no config.toml.


def test_a_start_with_no_id_starts_the_line_that_waits_for_nothing(tmp_path: Path) -> None:
    path = checkout_with(tmp_path, None, waits(checked=False))
    started = fgraph(["start"], path)
    assert (started.status, started.out) == (0, "started S-0002\n")


def test_the_line_started_with_no_id_is_in_progress(tmp_path: Path) -> None:
    path = checkout_with(tmp_path, None, waits(checked=False))
    fgraph(["start"], path)
    assert "  bucket       in-progress\n" in fgraph(["show", "S-0002"], path).out


def test_the_start_with_no_id_takes_the_id_status_names_as_next_to_start(tmp_path: Path) -> None:
    path = checkout_with(tmp_path, None, waits(checked=False))
    next_id = json.loads(fgraph(["status", "--format", "json"], path).out)["next_to_start"]
    assert fgraph(["start"], path).out == f"started {next_id}\n"


def test_a_reorder_changes_the_line_a_start_with_no_id_takes(tmp_path: Path) -> None:
    path = checkout_with(tmp_path, None, free(checked=False))
    fgraph(["reorder", "S-0002", "--before", "S-0001"], path)
    assert fgraph(["start"], path).out == "started S-0002\n"


def test_a_second_start_with_no_id_takes_the_next_line(tmp_path: Path) -> None:
    path = checkout_with(tmp_path, None, free(checked=False))
    fgraph(["start"], path)
    assert fgraph(["start"], path).out == "started S-0002\n"


def test_a_feature_on_top_starts_as_its_id_does(tmp_path: Path) -> None:
    path = checkout_with(
        tmp_path,
        None,
        [
            FEATURE,
            story(FIRST, "F-0001"),
            story(SECOND, "F-0001"),
            task("S-0001", checked=False),
            task("S-0002", checked=False),
        ],
    )
    assert fgraph(["start"], path).out == "started F-0001 with S-0001\n"


def test_a_start_with_no_id_refuses_a_line_waiting_for_a_started_one(tmp_path: Path) -> None:
    path = checkout_with(
        tmp_path,
        None,
        [
            *free(checked=False),
            ["start", "S-0001"],
            ["amend", "S-0002", "--depends-on", "S-0001"],
        ],
    )
    outcome = fgraph(["start"], path)
    assert (outcome.status, last(outcome)) == (2, [NONE.format("S-0002")])


def test_a_start_with_no_id_on_an_empty_record_says_the_backlog_is_empty(tmp_path: Path) -> None:
    path = checkout_with(tmp_path, None, [])
    outcome = fgraph(["start"], path)
    assert (outcome.status, last(outcome)) == (2, [EMPTY])


def test_a_start_with_no_id_refuses_a_story_with_no_task(tmp_path: Path) -> None:
    path = checkout_with(tmp_path, None, [story(FIRST)])
    outcome = fgraph(["start"], path)
    assert (outcome.status, last(outcome)) == (
        2,
        ["fgraph: error: S-0001 has no Task to start with"],
    )


def test_a_start_with_no_id_and_a_slug_says_the_development_is_off(tmp_path: Path) -> None:
    path = checkout_with(tmp_path, None, waits(checked=False))
    outcome = fgraph(["start", "--slug", "a-slug"], path)
    assert "".join(last(outcome)).startswith(NO_SLUG)


# Development on: a record with the development on and each Task checked.


def test_a_start_with_no_id_names_the_branch_and_the_worktree(tmp_path: Path) -> None:
    path = checkout_with(tmp_path, ON, waits(checked=True))
    worktree = tmp_path / "project.worktrees" / "S-0002-a-second-title"
    expected = f"started S-0002\nbranch wi/S-0002-a-second-title in {worktree}\n"
    assert fgraph(["start"], path).out == expected


def test_a_start_with_no_id_and_a_slug_names_the_slug_in_the_branch(tmp_path: Path) -> None:
    path = checkout_with(tmp_path, ON, waits(checked=True))
    assert "branch wi/S-0002-a-slug in " in fgraph(["start", "--slug", "a-slug"], path).out


def test_a_start_with_no_id_and_an_agent_records_the_agent(tmp_path: Path) -> None:
    path = checkout_with(tmp_path, ON, waits(checked=True))
    fgraph(["start", "--agent", "sonnet-a1"], path)
    assert "  agent        sonnet-a1\n" in fgraph(["show", "S-0002"], path).out


def test_a_start_with_no_id_passes_over_a_line_not_planned(tmp_path: Path) -> None:
    path = checkout_with(
        tmp_path,
        ON,
        [story(FIRST), story(SECOND), task("S-0002", checked=True)],
    )
    assert fgraph(["start"], path).out.splitlines()[:1] == ["started S-0002"]


def test_a_start_with_no_id_under_one_place_refuses_once_it_is_taken(tmp_path: Path) -> None:
    path = checkout_with(tmp_path, ONE, [*free(checked=True), ["start", "S-0001"]])
    outcome = fgraph(["start"], path)
    assert (outcome.status, last(outcome)) == (2, [NONE.format("S-0002")])


def test_a_start_with_no_id_takes_a_line_of_a_started_feature_first(tmp_path: Path) -> None:
    path = checkout_with(
        tmp_path,
        ON,
        [
            FEATURE,
            story(FIRST, "F-0001"),
            story(SECOND, "F-0001"),
            story(THIRD),
            task("S-0001", checked=True),
            task("S-0002", checked=True),
            task("S-0003", checked=True),
            ["start", "F-0001"],
        ],
    )
    assert fgraph(["start"], path).out.splitlines()[:1] == ["started S-0002"]


def test_a_start_with_no_id_in_a_worktree_is_held_to_main(tmp_path: Path) -> None:
    checkout_with(tmp_path, ON, [*free(checked=True), ["start", "S-0001"]])
    worktree = tmp_path / "project.worktrees" / "S-0001-a-first-title"
    outcome = fgraph(["start"], worktree)
    assert "".join(last(outcome)).startswith("fgraph: error: S-0002 starts on main, in ")


# Guards: green today and after the change.


def test_a_start_that_names_its_id_is_unchanged(tmp_path: Path) -> None:
    path = checkout_with(tmp_path, None, waits(checked=False))
    assert fgraph(["start", "S-0002"], path).out == "started S-0002\n"


def test_two_ids_on_a_start_are_refused(tmp_path: Path) -> None:
    path = checkout_with(tmp_path, None, waits(checked=False))
    assert fgraph(["start", "S-0001", "S-0002"], path).status == 2


def test_a_refused_start_with_no_id_writes_nothing(tmp_path: Path) -> None:
    path = checkout_with(
        tmp_path,
        None,
        [*free(checked=False), ["start", "S-0001"], ["amend", "S-0002", "--depends-on", "S-0001"]],
    )
    fgraph(["start"], path)
    assert (git(path, "status", "--porcelain"), git(path, "log", "-1", "--format=%s")) == (
        "",
        "chore: amend S-0002 in the record",
    )
