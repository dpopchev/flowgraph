"""A git command run in a work tree, and the refusal of one git exits non-zero on.

Every git step of the development runs through it: those of flowgraph.development.git and those
of a release, in flowgraph.development.tag_git, and the read of the configuration, in
flowgraph.development.config_git.
"""

import subprocess
from pathlib import Path


class GitError(Exception):
    """A git command that exited non-zero; the message names the command and its error output."""


def run_git(work_tree: Path, *args: str) -> str:
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
