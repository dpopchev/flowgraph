"""The criterion of a Feature closed tagged: with `delivery.tag` feature-close its close tags main.

The landing of the last work item of a started Feature completes the Feature and is followed by
the tag `fgraph release` makes; a landing that completes no Feature tags nothing, and neither
does one with `delivery.tag` none. Run end to end through `run` on a real git repository in a
temporary directory whose origin is a bare repository beside it, never a faked git; the identity
of its commits and its tags comes from the environment and no git config of the machine is read.
"""

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
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
STORY = ["add", "story", "Raise the Stories fgraph lists", *CRITERION]
UNDER_FEATURE = ["--parent", "F-0001"]


def add_task(story: str) -> list[str]:
    """The add of a Task under the Story, with a check, as the development needs one."""
    return ["add", "task", "a task title", "--parent", story, "--output", "out", "--check", "true"]


ONE_STORY = (ADD_FEATURE, [*STORY, *UNDER_FEATURE], add_task("S-0001"), ["start", "F-0001"])
TWO_STORIES = (*ONE_STORY[:3], [*STORY, *UNDER_FEATURE], add_task("S-0002"), ["start", "F-0001"])
ALONE = (STORY, add_task("S-0001"), ["start", "S-0001"])
LAND = ["land", "S-0001", "--message", "feat: land the first Story"]
WORKTREE = Path("project.worktrees") / "S-0001-raise-the-stories-fgraph"
DEVELOPMENT = "[development]\nenabled = true\n"
FEATURE_CLOSE = '[delivery]\ntag = "feature-close"\n'
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


def ready(tmp_path: Path, origin: Path, delivery: str, added: Sequence[Sequence[str]]) -> Path:
    """The checkout of main tracking the origin, S-0001 started and ready to land, delivery set.

    The commit that turns the development on is pushed; what is added is committed by fgraph,
    the one Task of S-0001 is worked and completed in the worktree of its branch, and the commit
    that writes the delivery table into the configuration is made last, on main.
    """
    checkout = tmp_path / "project"
    checkout.mkdir()
    git(checkout, "init", "--quiet", "--initial-branch", "main")
    config = checkout / ".fgraph" / "config.toml"
    config.parent.mkdir()
    config.write_text(DEVELOPMENT, encoding="utf-8")
    git(checkout, "add", ".fgraph/config.toml")
    git(checkout, "commit", "--quiet", "--message", "chore: turn the development on")
    git(checkout, "remote", "add", "origin", str(origin))
    git(checkout, "push", "--quiet", "--set-upstream", "origin", "main")
    for argv in added:
        fgraph(argv, checkout)
    worktree = tmp_path / WORKTREE
    fgraph(["start", "T-0001"], worktree)
    (worktree / "work.txt").write_text("the work of the Task\n", encoding="utf-8")
    git(worktree, "add", "work.txt")
    git(worktree, "commit", "--quiet", "--message", "feat: do the work of the Task")
    fgraph(["complete", "T-0001", "--commit", git(worktree, "rev-parse", "HEAD")], worktree)
    config.write_text(f"{DEVELOPMENT}{delivery}", encoding="utf-8")
    git(checkout, "commit", "--quiet", "--message", "chore: set the delivery", "--", str(config))
    return checkout


class TestTheLastStoryOfAFeatureLandedWithDeliveryTagFeatureClose:
    @pytest.fixture
    def checkout(self, tmp_path: Path, origin: Path) -> Path:
        return ready(tmp_path, origin, FEATURE_CLOSE, ONE_STORY)

    @pytest.fixture
    def landed(self, checkout: Path) -> Outcome:
        return fgraph(LAND, checkout)

    def test_land_exits_with_zero(self, landed: Outcome) -> None:
        assert landed.status == 0

    def test_land_names_the_tag_after_the_feature_completed(
        self, landed: Outcome, checkout: Path
    ) -> None:
        merge = git(checkout, "rev-parse", "--short", "main~1")
        assert landed.out == (
            f"landed S-0001 at {merge}\ncompleted F-0001 at {merge}\ntagged v0.1.0 at {merge}\n"
        )

    def test_main_holds_the_next_v_tag_on_the_commit_before_its_head(
        self, landed: Outcome, checkout: Path
    ) -> None:
        assert git(checkout, "tag", "--list", "--points-at", "main~1") == "v0.1.0"

    def test_the_tag_is_on_the_commit_of_the_landing_that_precedes_the_complete(
        self, landed: Outcome, checkout: Path
    ) -> None:
        assert git(checkout, "for-each-ref", "--format=%(*subject)", "refs/tags/v0.1.0") == (
            "feat: land the first Story"
        )

    def test_the_tag_is_annotated_as_fgraph_release_makes_it(
        self, landed: Outcome, checkout: Path
    ) -> None:
        assert git(checkout, "tag", "--list", "--format=%(objecttype) %(contents)", "v0.1.0") == (
            "tag release v0.1.0"
        )

    def test_the_origin_holds_no_tag_as_the_push_is_off(
        self, landed: Outcome, origin: Path
    ) -> None:
        assert (landed.status, git(origin, "tag", "--list")) == (0, "")


def test_the_close_of_a_feature_with_delivery_push_true_pushes_the_tag(
    tmp_path: Path, origin: Path
) -> None:
    checkout = ready(tmp_path, origin, f"{FEATURE_CLOSE}push = true\n", ONE_STORY)
    landed = fgraph(LAND, checkout)
    assert (landed.status, git(origin, "tag", "--list")) == (0, "v0.1.0")


def test_a_story_landed_before_the_last_of_its_feature_tags_nothing(
    tmp_path: Path, origin: Path
) -> None:
    checkout = ready(tmp_path, origin, FEATURE_CLOSE, TWO_STORIES)
    landed = fgraph(LAND, checkout)
    assert (landed.status, git(checkout, "tag", "--list")) == (0, "")


def test_a_story_that_stands_alone_landed_tags_nothing(tmp_path: Path, origin: Path) -> None:
    checkout = ready(tmp_path, origin, FEATURE_CLOSE, ALONE)
    landed = fgraph(LAND, checkout)
    assert (landed.status, git(checkout, "tag", "--list")) == (0, "")


def test_the_close_of_a_feature_with_delivery_tag_none_tags_nothing(
    tmp_path: Path, origin: Path
) -> None:
    checkout = ready(tmp_path, origin, '[delivery]\ntag = "none"\n', ONE_STORY)
    landed = fgraph(LAND, checkout)
    assert (landed.status, git(checkout, "tag", "--list")) == (0, "")
