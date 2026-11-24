"""The criterion of a work item delivered: a landing gates, tags and pushes before it completes.

With the development on, a gate that passes and `[delivery]` set to push main and to tag, the
landing of a work item tags main with its version on the commit of the landing, after main is
pushed and before the write that completes; a tag the origin refuses leaves the work item merged
and not completed. Run end to end through `run` on a real git repository in a temporary
directory whose origin is a bare repository beside it, never a faked git; the identity of its
commits and its tags comes from the environment and no git config of the machine is read.
"""

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, open_git, read_config, run, run_gate

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
STORY = ["add", "story", "Raise the Stories fgraph lists", *CRITERION]
ADD_UPKEEP = ["add", "upkeep", "Keep the Stories fgraph lists", *CRITERION]
UNDER_FEATURE = ["--parent", "F-0001"]


def add_task(item: str) -> list[str]:
    """The add of a Task under the work item, with a check, as the development needs one."""
    return ["add", "task", "a task title", "--parent", item, "--output", "out", "--check", "true"]


ONE_STORY = (ADD_FEATURE, [*STORY, *UNDER_FEATURE], add_task("S-0001"), ["start", "F-0001"])
TWO_STORIES = (*ONE_STORY[:3], [*STORY, *UNDER_FEATURE], add_task("S-0002"), ["start", "F-0001"])
ALONE = (STORY, add_task("S-0001"), ["start", "S-0001"])
AN_UPKEEP = (ADD_UPKEEP, add_task("U-0001"), ["start", "U-0001"])
LAND = ["land", "S-0001", "--message", "feat: land the first Story"]
LAND_UPKEEP = ["land", "U-0001", "--message", "feat: land the first Upkeep"]
DEVELOPMENT = '[development]\nenabled = true\ngate = "test -f work.txt"\n'
FAILING_GATE = '[development]\nenabled = true\ngate = "exit 3"\n'
CLOSE = '[delivery]\npush = true\ntag = "close"\n'
FEATURE_CLOSE = '[delivery]\npush = true\ntag = "feature-close"\n'
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path) -> Outcome:
    """Run the command in cwd, whose record is `.fgraph/`, on its files and the real git."""
    out: list[str] = []
    err: list[str] = []
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
        run_gate=run_gate,
        run_check=lambda command, directory: 0,
    )
    return Outcome(status, "".join(out), "".join(err))


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


@pytest.fixture(autouse=True)
def environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The identity of every commit and tag from the environment, and no git config."""
    for name, value in IDENTITY.items():
        monkeypatch.setenv(name, value)
    empty = tmp_path / "gitconfig"
    empty.touch()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


@pytest.fixture
def origin(tmp_path: Path) -> Path:
    """A bare repository on main, the origin of the project."""
    path = tmp_path / "origin.git"
    git(tmp_path, "init", "--quiet", "--bare", "--initial-branch", "main", str(path))
    return path


def ready(
    tmp_path: Path,
    origin: Path,
    delivery: str,
    added: Sequence[Sequence[str]],
    development: str = DEVELOPMENT,
) -> Path:
    """The checkout of main tracking the origin, the first work item started and ready to land.

    The commit that turns the development on is pushed; what is added is committed by fgraph,
    the one Task of the work item started is worked and completed in the worktree of its branch,
    and the commit that writes the delivery table into the configuration is made last, on main:
    the word of `delivery.tag` is read from it on.
    """
    checkout = tmp_path / "project"
    checkout.mkdir()
    git(checkout, "init", "--quiet", "--initial-branch", "main")
    config = checkout / ".fgraph" / "config.toml"
    config.parent.mkdir()
    config.write_text(development, encoding="utf-8")
    git(checkout, "add", ".fgraph/config.toml")
    git(checkout, "commit", "--quiet", "--message", "chore: turn the development on")
    git(checkout, "remote", "add", "origin", str(origin))
    git(checkout, "push", "--quiet", "--set-upstream", "origin", "main")
    for argv in added:
        fgraph(argv, checkout)
    (worktree,) = (tmp_path / "project.worktrees").iterdir()
    fgraph(["start", "T-0001"], worktree)
    (worktree / "work.txt").write_text("the work of the Task\n", encoding="utf-8")
    git(worktree, "add", "work.txt")
    git(worktree, "commit", "--quiet", "--message", "feat: do the work of the Task")
    fgraph(["complete", "T-0001", "--commit", git(worktree, "rev-parse", "HEAD")], worktree)
    config.write_text(f"{development}{delivery}", encoding="utf-8")
    git(checkout, "commit", "--quiet", "--message", "chore: set the delivery", "--", str(config))
    return checkout


def tag_by_hand(checkout: Path) -> None:
    """Tag main v0.1.0, annotated, as a release before the landing."""
    git(checkout, "tag", "--annotate", "--message", "release v0.1.0", "v0.1.0", "main")


class TestAStoryThatStandsAloneLanded:
    @pytest.fixture
    def checkout(self, tmp_path: Path, origin: Path) -> Path:
        return ready(tmp_path, origin, CLOSE, ALONE)

    @pytest.fixture
    def landed(self, checkout: Path) -> Outcome:
        return fgraph(LAND, checkout)

    def test_land_exits_with_zero_and_says_the_four_lines(
        self, landed: Outcome, checkout: Path
    ) -> None:
        sha = git(checkout, "rev-parse", "--short", "main~1")
        assert (landed.status, landed.out) == (
            0,
            f"landed S-0001 at {sha}\nrun: an action -> another\npushed main to origin\n"
            f"tagged v0.1.0 at {sha}\npushed v0.1.0 to origin\n",
        )

    def test_show_lists_it_completed(self, landed: Outcome, checkout: Path) -> None:
        assert "bucket       completed" in fgraph(["show", "S-0001"], checkout).out

    def test_main_of_the_origin_is_main_of_the_checkout(
        self, landed: Outcome, checkout: Path, origin: Path
    ) -> None:
        assert git(origin, "rev-parse", "main") == git(checkout, "rev-parse", "main")

    def test_the_origin_holds_the_tag(self, landed: Outcome, origin: Path) -> None:
        assert git(origin, "tag", "--list") == "v0.1.0"

    def test_the_tag_of_the_origin_is_on_the_merge_of_the_story(
        self, landed: Outcome, checkout: Path, origin: Path
    ) -> None:
        tagged = git(origin, "for-each-ref", "--format=%(*objectname:short)", "refs/tags/v0.1.0")
        assert tagged == git(checkout, "rev-parse", "--short", "main~1")

    def test_the_tag_is_annotated_release_v0_1_0(self, landed: Outcome, origin: Path) -> None:
        assert git(origin, "tag", "--list", "--format=%(objecttype) %(contents)", "v0.1.0") == (
            "tag release v0.1.0"
        )


@pytest.mark.parametrize(
    ("added", "argv", "expected"),
    [(ALONE, LAND, "v0.2.0"), (AN_UPKEEP, LAND_UPKEEP, "v0.1.1")],
    ids=["a-story", "an-upkeep"],
)
def test_the_version_follows_the_kind_of_the_work_item(
    added: Sequence[Sequence[str]],
    argv: Sequence[str],
    expected: str,
    tmp_path: Path,
    origin: Path,
) -> None:
    checkout = ready(tmp_path, origin, CLOSE, added)
    tag_by_hand(checkout)
    fgraph(argv, checkout)
    assert git(checkout, "tag", "--list", "--points-at", "main~1") == expected


def test_a_story_under_a_feature_that_is_not_its_last_tags_nothing(
    tmp_path: Path, origin: Path
) -> None:
    checkout = ready(tmp_path, origin, CLOSE, TWO_STORIES)
    landed = fgraph(LAND, checkout)
    assert (landed.status, git(checkout, "tag", "--list")) == (0, "")


def test_the_last_story_of_a_feature_is_tagged_at_its_close(tmp_path: Path, origin: Path) -> None:
    checkout = ready(tmp_path, origin, CLOSE, ONE_STORY)
    fgraph(LAND, checkout)
    assert git(checkout, "tag", "--list") == "v0.1.0"


class TestTheLastStoryOfAFeatureWhoseTagTheOriginRefuses:
    @pytest.fixture
    def checkout(self, tmp_path: Path, origin: Path) -> Path:
        checkout = ready(tmp_path, origin, FEATURE_CLOSE, ONE_STORY)
        git(origin, "tag", "v0.1.0", "main")
        return checkout

    @pytest.fixture
    def refused(self, checkout: Path) -> Outcome:
        return fgraph(LAND, checkout)

    def test_land_exits_with_two_and_the_error_ends_naming_the_merge_and_the_way_back(
        self, refused: Outcome, checkout: Path
    ) -> None:
        sha = git(checkout, "rev-parse", "--short", "main")
        ending = (
            f"-- v0.1.0 is tagged at {sha}, it is not pushed"
            f" -- S-0001 is merged at {sha} and not completed -- run fgraph land S-0001 again\n"
        )
        assert (refused.status, refused.err.endswith(ending)) == (2, True)

    def test_show_lists_the_story_in_progress(self, refused: Outcome, checkout: Path) -> None:
        assert "bucket       in-progress" in fgraph(["show", "S-0001"], checkout).out

    def test_show_lists_the_feature_in_progress(self, refused: Outcome, checkout: Path) -> None:
        assert "bucket       in-progress" in fgraph(["show", "F-0001"], checkout).out


def test_the_tag_at_the_close_of_a_feature_is_on_the_commit_of_the_landing(
    tmp_path: Path, origin: Path
) -> None:
    checkout = ready(tmp_path, origin, FEATURE_CLOSE, ONE_STORY)
    fgraph(LAND, checkout)
    tagged = git(checkout, "for-each-ref", "--format=%(*objectname:short)", "refs/tags/v0.1.0")
    assert tagged == git(checkout, "rev-parse", "--short", "main~1")


class TestAStoryWhoseGateFails:
    @pytest.fixture
    def checkout(self, tmp_path: Path, origin: Path) -> Path:
        return ready(tmp_path, origin, FEATURE_CLOSE, ONE_STORY, FAILING_GATE)

    @pytest.fixture
    def before(self, checkout: Path, origin: Path) -> str:
        return git(origin, "rev-parse", "main")

    @pytest.fixture
    def refused(self, checkout: Path, before: str) -> Outcome:
        return fgraph(LAND, checkout)

    def test_land_exits_with_two(self, refused: Outcome) -> None:
        assert refused.status == 2

    def test_show_lists_the_story_in_progress(self, refused: Outcome, checkout: Path) -> None:
        assert "bucket       in-progress" in fgraph(["show", "S-0001"], checkout).out

    def test_no_tag_is_made(self, refused: Outcome, checkout: Path) -> None:
        assert git(checkout, "tag", "--list") == ""

    def test_main_of_the_origin_is_where_it_was(
        self, refused: Outcome, before: str, origin: Path
    ) -> None:
        assert git(origin, "rev-parse", "main") == before
