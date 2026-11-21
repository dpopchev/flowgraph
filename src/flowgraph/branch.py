"""The branch of a started work item: its slug, its name and the worktree it is checked out in.

The branch is `wi/<id>-<slug>`, checked out at `<parent>/<checkout name>.worktrees/<id>-<slug>`.
"""

import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from flowgraph.work_item import WorkItemId, work_item_id_text

# The words of a title its slug is made of, when no slug is given.
SLUG_WORDS = 4

# Lower-case letters and digits, in words joined by one hyphen.
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


@dataclass(frozen=True)
class Slug:
    """The words of a branch name after the id: lower-case letters and digits joined by hyphens."""

    text: str


@dataclass(frozen=True)
class Branch:
    """The branch of a work item and the path of the worktree it is checked out in."""

    name: str
    path: Path


class SlugError(ValueError):
    """A text that is no slug."""


def make_slug(text: str) -> Slug:
    """The slug written as the text.

    Raises SlugError when it is empty or holds anything but lower-case ASCII letters and digits
    in words joined by one hyphen.
    """
    if SLUG.fullmatch(text) is None:
        raise SlugError(
            f"{text!r} is no slug: it is lower-case letters and digits joined by hyphens"
        )
    return Slug(text)


def slug_of_title(title: str) -> Slug:
    """The slug of a title: its first four words, lower-cased, each kept to its letters and digits.

    A word left with no letter or digit is skipped. Raises SlugError when no word is left.
    """
    words = [re.sub(r"[^a-z0-9]", "", word) for word in title.lower().split()]
    return make_slug("-".join([word for word in words if word][:SLUG_WORDS]))


def branch_of(item: WorkItemId, slug: Slug, checkout: Path) -> Branch:
    """The branch of the work item and its worktree, beside the checkout it is made from."""
    leaf = f"{work_item_id_text(item)}-{slug.text}"
    return Branch(f"wi/{leaf}", checkout.parent / f"{checkout.name}.worktrees" / leaf)


class GitError(Exception):
    """A git command that exited non-zero; the message names the command and its error output."""


def _git(work_tree: Path, *args: str) -> str:
    """Adapter: the output of the git command run in the work tree, stripped.

    Raises GitError naming the command and its error output when it exits non-zero.
    """
    try:
        done = subprocess.run(
            ["git", *args], cwd=work_tree, check=True, capture_output=True, text=True
        )
    except subprocess.CalledProcessError as error:
        command = " ".join(["git", *args])
        raise GitError(f"{command} failed: {error.stderr.strip()}") from error
    return done.stdout.strip()


def work_tree_of(directory: Path) -> Path | None:
    """Adapter: the top of the git work tree the directory is inside, or None when it is in none."""
    try:
        return Path(_git(directory, "rev-parse", "--show-toplevel"))
    except GitError:
        return None


def commit_files(work_tree: Path, files: Sequence[Path], message: str) -> str:
    """Adapter: commit the files, relative to the work tree, alone with the message; its sha.

    Whatever else is staged or changed stays as it was and out of the commit. Raises GitError
    when git refuses a step; a commit refused leaves the files unstaged.
    """
    named = [str(file) for file in files]
    _git(work_tree, "add", "--", *named)
    try:
        _git(work_tree, "commit", "--quiet", "--only", "--message", message, "--", *named)
    except GitError:
        _git(work_tree, "reset", "--quiet", "--", *named)
        raise
    return _git(work_tree, "rev-parse", "HEAD")


def add_worktree(work_tree: Path, branch: str, path: Path, commit: str) -> None:
    """Adapter: check out a new branch at the commit in a new worktree at the path.

    Raises GitError when git refuses it, as when the branch or the path exists already.
    """
    _git(work_tree, "worktree", "add", "--quiet", "-b", branch, str(path), commit)


def current_branch(work_tree: Path) -> str:
    """Adapter: the branch the work tree is on; empty when it is on none."""
    return _git(work_tree, "branch", "--show-current")


def branches_like(work_tree: Path, pattern: str) -> list[str]:
    """Adapter: the branches of the repository whose name matches the pattern, by name."""
    return _git(work_tree, "branch", "--list", "--format=%(refname:short)", pattern).splitlines()


def _merging(work_tree: Path) -> bool:
    """True while a merge is held in the work tree, not yet committed."""
    try:
        _git(work_tree, "rev-parse", "--quiet", "--verify", "MERGE_HEAD")
    except GitError:
        return False
    return True


def abort_merge(work_tree: Path) -> None:
    """Adapter: drop the merge held in the work tree; nothing changes when none is held."""
    if _merging(work_tree):
        _git(work_tree, "merge", "--abort")


def merge_uncommitted(work_tree: Path, branch: str) -> None:
    """Adapter: merge the branch into the work tree as a merge of its own, held uncommitted.

    Raises GitError when git refuses the merge, as on a conflict; nothing is merged then.
    """
    try:
        _git(work_tree, "merge", "--no-ff", "--no-commit", "--quiet", branch)
    except GitError:
        abort_merge(work_tree)
        raise


def commit_merge(work_tree: Path, message: str) -> str:
    """Adapter: commit the merge held in the work tree under the message; its short sha.

    Raises GitError when git refuses the commit; the merge is then still held.
    """
    _git(work_tree, "commit", "--quiet", "--message", message)
    return _git(work_tree, "rev-parse", "--short", "HEAD")


def worktree_of_branch(work_tree: Path, branch: str) -> Path | None:
    """Adapter: the worktree the branch is checked out in, or None when it is in none."""
    path = None
    for line in _git(work_tree, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            path = Path(line.removeprefix("worktree "))
        if line == f"branch refs/heads/{branch}":
            return path
    return None


def remove_worktree(work_tree: Path, path: Path) -> None:
    """Adapter: remove the worktree at the path.

    Raises GitError when git refuses it, as when it holds a change or an untracked file.
    """
    _git(work_tree, "worktree", "remove", str(path))


def delete_branch(work_tree: Path, branch: str) -> None:
    """Adapter: delete the branch; raises GitError when it is not merged or is checked out."""
    _git(work_tree, "branch", "--quiet", "-d", branch)
