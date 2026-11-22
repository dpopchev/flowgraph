"""The git adapters of a release, against the real git in a temporary directory.

The identity of every commit and tag comes from the environment and no git config is read; a
tag is pushed to a bare origin beside the repository.
"""

import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from flowgraph.development.git import GitError
from flowgraph.development.tag_git import holds_commit, make_tag, push_tag, tagged_at, tags_like

pytestmark = pytest.mark.edge

IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def commit(cwd: Path, name: str) -> str:
    """Commit a file of that name in cwd; the sha of the commit."""
    (cwd / name).write_text(f"{name}\n", encoding="utf-8")
    git(cwd, "add", name)
    git(cwd, "commit", "--quiet", "--message", f"write {name}")
    return git(cwd, "rev-parse", "HEAD")


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
def checkout(tmp_path: Path) -> Path:
    """A git repository on main with one commit, README, and no remote."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    commit(path, "README")
    return path


@pytest.fixture
def origin(tmp_path: Path) -> Path:
    """A bare repository on main."""
    path = tmp_path / "origin.git"
    git(tmp_path, "init", "--quiet", "--bare", "--initial-branch", "main", str(path))
    return path


@pytest.fixture
def tracking(checkout: Path, origin: Path) -> Path:
    """The checkout with main pushed to the origin and tracking it."""
    git(checkout, "remote", "add", "origin", str(origin))
    git(checkout, "push", "--quiet", "--set-upstream", "origin", "main")
    return checkout


def test_the_tags_like_a_pattern_are_listed_by_name(checkout: Path) -> None:
    for tag in ("v0.2.0", "v0.1.0", "latest"):
        git(checkout, "tag", tag)
    assert tags_like(checkout, "v*") == ["v0.1.0", "v0.2.0"]


def test_a_repository_without_a_tag_lists_none(checkout: Path) -> None:
    assert tags_like(checkout, "v*") == []


def test_a_tag_holds_a_commit_it_was_made_after(checkout: Path) -> None:
    first = git(checkout, "rev-parse", "HEAD")
    commit(checkout, "work.txt")
    git(checkout, "tag", "v0.1.0")
    assert holds_commit(checkout, "v0.1.0", first) is True


def test_a_tag_does_not_hold_a_commit_made_after_it(checkout: Path) -> None:
    git(checkout, "tag", "v0.1.0")
    assert holds_commit(checkout, "v0.1.0", commit(checkout, "work.txt")) is False


def test_a_commit_git_does_not_know_is_held_by_no_answer(checkout: Path) -> None:
    git(checkout, "tag", "v0.1.0")
    assert holds_commit(checkout, "v0.1.0", "abc1234") is None


def test_the_time_of_an_annotated_tag_is_when_it_was_made(checkout: Path) -> None:
    git(checkout, "tag", "--annotate", "--message", "a release", "v0.1.0")
    made = git(checkout, "for-each-ref", "--format=%(taggerdate:iso-strict)", "refs/tags/v0.1.0")
    assert tagged_at(checkout, "v0.1.0") == datetime.fromisoformat(made)


def test_the_time_of_a_tag_git_does_not_hold_raises_naming_it(checkout: Path) -> None:
    with pytest.raises(GitError, match=r"^v0\.1\.0 is no tag of the repository$"):
        tagged_at(checkout, "v0.1.0")


class TestATagMade:
    @pytest.fixture
    def made(self, checkout: Path) -> str:
        return make_tag(checkout, "v0.1.0", "release v0.1.0", "main")

    def test_it_names_the_short_sha_of_the_commit_it_tags(self, made: str, checkout: Path) -> None:
        assert made == git(checkout, "rev-parse", "--short", "main")

    def test_it_is_annotated(self, made: str, checkout: Path) -> None:
        assert git(checkout, "cat-file", "-t", "v0.1.0") == "tag"

    def test_it_carries_the_message(self, made: str, checkout: Path) -> None:
        assert git(checkout, "tag", "--list", "--format=%(contents:subject)", "v0.1.0") == (
            "release v0.1.0"
        )

    def test_it_is_on_the_head_of_the_branch(self, made: str, checkout: Path) -> None:
        assert git(checkout, "rev-parse", "v0.1.0^{commit}") == git(checkout, "rev-parse", "main")


def test_a_tag_that_exists_is_refused_and_left_where_it_is(checkout: Path) -> None:
    git(checkout, "tag", "--annotate", "--message", "a release", "v0.1.0")
    before = git(checkout, "rev-parse", "v0.1.0")
    commit(checkout, "work.txt")
    with pytest.raises(GitError):
        make_tag(checkout, "v0.1.0", "release v0.1.0", "main")
    assert git(checkout, "rev-parse", "v0.1.0") == before


def test_a_tag_pushed_is_held_by_the_origin(tracking: Path, origin: Path) -> None:
    git(tracking, "tag", "--annotate", "--message", "a release", "v0.1.0")
    push_tag(tracking, "main", "v0.1.0")
    assert git(origin, "rev-parse", "v0.1.0") == git(tracking, "rev-parse", "v0.1.0")


def test_a_tag_pushed_names_the_remote_of_the_branch(tracking: Path) -> None:
    git(tracking, "tag", "--annotate", "--message", "a release", "v0.1.0")
    assert push_tag(tracking, "main", "v0.1.0") == "origin"


def test_a_tag_pushed_from_a_branch_that_tracks_no_remote_raises_naming_it(
    checkout: Path,
) -> None:
    git(checkout, "tag", "--annotate", "--message", "a release", "v0.1.0")
    with pytest.raises(GitError, match=r"^main tracks no branch of a remote to push to$"):
        push_tag(checkout, "main", "v0.1.0")
