"""The git steps of the development: each an adapter that runs git in a work tree.

The commit of a write, the worktree of a branch, the merges of a landing and the cleanup after
it; each raises GitError naming the command and its error output when git refuses it.
"""

import subprocess
from collections.abc import Sequence
from pathlib import Path

from flowgraph.development.branch import MAIN


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


def ignores(work_tree: Path, path: Path) -> bool:
    """Adapter: True when a rule git reads in the work tree names the path, tracked or not.

    A relative path is taken from the working directory, as it was located. Raises GitError
    naming the command when git cannot tell, as of a path outside the work tree.
    """
    command = ["git", "check-ignore", "--quiet", "--no-index", "--", str(path.resolve())]
    done = subprocess.run(command, cwd=work_tree, check=False, capture_output=True, text=True)
    if done.returncode > 1:
        raise GitError(f"{' '.join(command)} failed: {done.stderr.strip()}")
    return done.returncode == 0


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


def changed_files(work_tree: Path, commit: str) -> list[str] | None:
    """Adapter: the files the commit changed, as paths from the top of the work tree.

    A merge commit answers with what it brought to its first parent. A sha git does not know as
    a commit answers with None.
    """
    try:
        _git(work_tree, "rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}")
    except GitError:
        return None
    shown = _git(work_tree, "show", "--first-parent", "--name-only", "--format=", "-z", commit)
    return [name for name in shown.split("\0") if name]


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
    """Adapter: drop the merge held in the work tree; nothing changes when none is held.

    The files the merge brought are put back as HEAD holds them first, so a change made to one
    of them since, as by a gate, goes with the merge, which git would refuse to drop otherwise;
    a change to any other file stays. A merge starts from an index that HEAD holds, so the files
    staged are those the merge brought.
    """
    if not _merging(work_tree):
        return
    brought = _git(work_tree, "diff", "--cached", "--name-only").splitlines()
    if brought:
        _git(work_tree, "restore", "--source=HEAD", "--staged", "--worktree", "--", *brought)
    _git(work_tree, "merge", "--abort")


def merge_uncommitted(work_tree: Path, branch: str) -> None:
    """Adapter: merge the branch into the work tree as a merge of its own, held uncommitted.

    Raises GitError when a merge is held in the work tree already, which is left as it was; when
    git refuses the merge, as on a conflict, nothing is merged then; and when the branch brings
    no commit to merge, so no merge is held and nothing staged is taken into a commit.
    """
    if _merging(work_tree):
        raise GitError(f"a merge is held in {work_tree}: commit it or abort it first")
    try:
        _git(work_tree, "merge", "--no-ff", "--no-commit", "--quiet", branch)
    except GitError:
        abort_merge(work_tree)
        raise
    if not _merging(work_tree):
        raise GitError(f"{branch} brings nothing to merge: it holds no commit {MAIN} lacks")


def commit_merge(work_tree: Path, message: str) -> str:
    """Adapter: commit the merge held in the work tree under the message; its short sha.

    Raises GitError when git refuses the commit; the merge is then still held.
    """
    _git(work_tree, "commit", "--quiet", "--message", message)
    return _git(work_tree, "rev-parse", "--short", "HEAD")


def commit_squash(work_tree: Path, message: str) -> str:
    """Adapter: commit the merge held in the work tree as one commit of its branch alone.

    The commit holds what the merge brought under the message and has one parent; its short sha
    is returned. The merge is held as one of its own and not by `git merge --squash`, which takes
    a staged change of the work tree into the commit. Raises GitError when git refuses the
    commit; nothing is merged then, and a change that is not staged stays.
    """
    _git(work_tree, "merge", "--quit")
    try:
        _git(work_tree, "commit", "--quiet", "--message", message)
    except GitError:
        _git(work_tree, "reset", "--merge")
        raise
    return _git(work_tree, "rev-parse", "--short", "HEAD")


def can_fast_forward(work_tree: Path, branch: str) -> bool:
    """Adapter: True when the branch holds every commit the work tree is on.

    Raises GitError naming the command when git cannot tell, as of a branch that is none.
    """
    command = ["git", "merge-base", "--is-ancestor", "HEAD", branch]
    done = subprocess.run(command, cwd=work_tree, check=False, capture_output=True, text=True)
    if done.returncode > 1:
        raise GitError(f"{' '.join(command)} failed: {done.stderr.strip()}")
    return done.returncode == 0


def fast_forward(work_tree: Path, branch: str) -> str:
    """Adapter: move the branch of the work tree to the tip of the branch; its short sha.

    No commit is made. Raises GitError when the work tree is on a commit the branch lacks;
    nothing is merged then.
    """
    _git(work_tree, "merge", "--ff-only", "--quiet", branch)
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


def worktrees(work_tree: Path) -> list[Path]:
    """Adapter: every worktree of the repository of the work tree, its first checkout first."""
    listed = _git(work_tree, "worktree", "list", "--porcelain").splitlines()
    return [Path(line.removeprefix("worktree ")) for line in listed if line.startswith("worktree ")]


def remove_worktree(work_tree: Path, path: Path) -> None:
    """Adapter: remove the worktree at the path.

    Raises GitError when git refuses it, as when it holds a change or an untracked file.
    """
    _git(work_tree, "worktree", "remove", str(path))


def delete_branch(work_tree: Path, branch: str) -> None:
    """Adapter: delete the branch; raises GitError when it is not merged or is checked out."""
    _git(work_tree, "branch", "--quiet", "-d", branch)


def delete_unmerged_branch(work_tree: Path, branch: str) -> None:
    """Adapter: delete the branch, merged or not; raises GitError when it is checked out.

    The step of a branch landed by squash, whose commits main never holds.
    """
    _git(work_tree, "branch", "--quiet", "-D", branch)
