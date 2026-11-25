"""The files the next commit of a work tree can hold, read before it is made (S-0153)."""

from pathlib import Path

from flowgraph.development.git_command import run_git


def uncommitted_files(work_tree: Path) -> list[str]:
    """Adapter: the files changed in the work tree and not committed, as paths from its top.

    The tracked files changed since HEAD, staged or not, and the files git neither tracks nor
    ignores; sorted, each once. Raises GitError naming the command when git refuses, as
    `git diff HEAD` does in a repository with no commit.
    """
    tracked = run_git(work_tree, "diff", "--name-only", "-z", "HEAD")
    untracked = run_git(
        work_tree, "ls-files", "--others", "--exclude-standard", "--full-name", "-z"
    )
    parts = (*tracked.split("\0"), *untracked.split("\0"))
    return sorted({part for part in parts if part})
