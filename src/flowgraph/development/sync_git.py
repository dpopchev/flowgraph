"""The git steps of fgraph sync: each an adapter that runs git in a work tree, on its branch.

Whether the work tree holds a change not committed, whether its head holds the commits of a
branch, the merge of a branch into it and its head. Each raises GitError naming the command when
git refuses it.
"""

from pathlib import Path

from flowgraph.development.git_command import GitError, run_git


def uncommitted(work_tree: Path) -> list[str]:
    """Adapter: the tracked files changed since HEAD, staged or not; an untracked one is not."""
    return run_git(work_tree, "diff", "--name-only", "HEAD").splitlines()


def holds(work_tree: Path, branch: str) -> bool:
    """Adapter: True when HEAD holds every commit of the branch.

    Raises GitError naming the command when git cannot tell, as of a branch that is none.
    """
    return run_git(work_tree, "rev-list", "--count", f"HEAD..refs/heads/{branch}") == "0"


def merge_branch(work_tree: Path, branch: str, message: str) -> list[str]:
    """Adapter: merge the branch into the work tree by one merge commit under the message.

    Never a fast-forward. Answers [] once the merge commit is made; on a conflict the merge is
    aborted, the work tree as it was, and the files in conflict are answered. Raises GitError
    when git refuses with no file in conflict, as for an untracked file the merge would overwrite.
    """
    try:
        run_git(
            work_tree,
            "merge",
            "--no-ff",
            "--no-edit",
            "--quiet",
            "--message",
            message,
            f"refs/heads/{branch}",
        )
    except GitError:
        files = run_git(work_tree, "diff", "--name-only", "--diff-filter=U").splitlines()
        if not files:
            raise
        run_git(work_tree, "merge", "--abort")  # a file in conflict means a merge is held
        return files
    return []


def head_of(work_tree: Path) -> str:
    """Adapter: the short sha of HEAD."""
    return run_git(work_tree, "rev-parse", "--short", "HEAD")
