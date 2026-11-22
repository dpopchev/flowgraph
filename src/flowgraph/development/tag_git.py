"""The git steps of a release: each an adapter that runs git in a work tree, on its tags.

The tags of the repository, whether a tag holds a commit and when it was made, the annotated tag
made on the head of a branch and its push. A tag is never moved or deleted: one that exists is
refused by git. Each raises GitError naming the command when git refuses it.
"""

import subprocess
from datetime import datetime
from pathlib import Path

from flowgraph.development.git import upstream_of
from flowgraph.development.git_command import GitError, run_git


def tags_like(work_tree: Path, pattern: str) -> list[str]:
    """Adapter: the tags of the repository whose name matches the pattern, by name."""
    return run_git(work_tree, "tag", "--list", pattern).splitlines()


def holds_commit(work_tree: Path, tag: str, commit: str) -> bool | None:
    """Adapter: True when the commit the tag is on is the commit or comes after it.

    A sha git does not know as a commit answers with None. Raises GitError naming the command
    when git cannot tell, as of a tag that is none.
    """
    try:
        run_git(work_tree, "rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}")
    except GitError:
        return None
    command = ["git", "merge-base", "--is-ancestor", commit, f"refs/tags/{tag}"]
    done = subprocess.run(command, cwd=work_tree, check=False, capture_output=True, text=True)
    if done.returncode > 1:
        raise GitError(f"{' '.join(command)} failed: {done.stderr.strip()}")
    return done.returncode == 0


def tagged_at(work_tree: Path, tag: str) -> datetime:
    """Adapter: when the tag was made, the time of its commit for a tag that is not annotated.

    Raises GitError naming the tag when the repository holds none of that name.
    """
    made = run_git(
        work_tree, "for-each-ref", "--format=%(creatordate:iso-strict)", f"refs/tags/{tag}"
    )
    if not made:
        raise GitError(f"{tag} is no tag of the repository")
    return datetime.fromisoformat(made)


def make_tag(work_tree: Path, tag: str, message: str, branch: str) -> str:
    """Adapter: tag the head of the branch with an annotated tag under the message; its short sha.

    Raises GitError when git refuses it, as when the tag exists: that one stays where it is.
    """
    run_git(work_tree, "tag", "--annotate", "--message", message, tag, f"refs/heads/{branch}")
    return run_git(work_tree, "rev-parse", "--short", f"refs/tags/{tag}^{{commit}}")


def push_tag(work_tree: Path, branch: str, tag: str) -> str:
    """Adapter: push the tag to the remote the branch tracks; the name of the remote.

    Raises GitError when the branch tracks none, and naming the command when git refuses the push,
    as when the remote holds a tag of that name already.
    """
    remote, _ = upstream_of(work_tree, branch)
    run_git(work_tree, "push", "--quiet", remote, f"refs/tags/{tag}:refs/tags/{tag}")
    return remote
