"""The git read of the history of a path: whether a commit the history of HEAD holds changed it.

So fgraph about answers for a file a later commit deleted (S-0080); one git log, the path read
literally.
"""

from pathlib import Path

from flowgraph.development.git_command import GitError, run_git

NUL = "\0"


def touched_path(work_tree: Path, path: str) -> bool:
    """Adapter: true when a commit of the history of HEAD changed the file at the path.

    The path is from the top of the work tree, which git runs in (a pathspec is read from the
    directory git runs in); literal, so `*.txt` is no pattern; `--full-history`, so a file added
    and deleted on a branch merged since is found; `--no-renames`, so a file a commit renamed is
    listed under its old name; the name must be listed as given, so a directory, whose files git
    lists, is no file; a merge brings no name of its own; a commit only another branch holds is
    not read. Raises GitError naming the command when git refuses the log.
    """
    try:
        run_git(work_tree, "rev-parse", "--verify", "--quiet", "HEAD")
    except GitError:
        return False
    shown = run_git(
        work_tree,
        "--literal-pathspecs",
        "log",
        "--full-history",
        "--no-renames",
        "--format=",
        "--name-only",
        "-z",
        "HEAD",
        "--",
        path,
    )
    return path in shown.split(NUL)
