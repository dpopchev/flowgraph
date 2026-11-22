"""The commit of a write of the record: fgraph commits the files the write changed, alone.

Every write shares this one step. With the development turned on in the configuration of the
record, the start of a work item also checks its branch out at that commit, in a worktree of its
own. Outside a git work tree a write is left as its files, and so is the write of a record git
ignores, whose start branches at HEAD, and every write of a record whose configuration turns
the commits off.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Never

from flowgraph import branch
from flowgraph.branch import GitError, branch_of
from flowgraph.config import Config
from flowgraph.item import ToBranch, Written
from flowgraph.store import Store
from flowgraph.work_item import work_item_id_text

# Where the branch of a start is checked out when the write of the record made no commit.
HEAD = "HEAD"


def _ignores_nothing(path: Path) -> bool:
    """The `ignores` of a work tree built without it: git ignores no path there."""
    return False


def _lands_nothing(*_: object) -> Never:
    """A step of a landing in a work tree built without them: a contract, it lands nothing."""
    raise AssertionError("a work tree built without the steps of a landing takes none")


@dataclass(frozen=True)
class LandingSteps:
    """The steps only a landing takes in a work tree, each bound to it.

    `merge` merges a branch as a merge of its own, held uncommitted, and merges nothing when git
    refuses; `abort_merge` drops a merge held; `commit_merge` commits it under a message and
    returns its short sha; `commit_squash` commits it as one commit of the branch of the work
    tree alone, and merges nothing when git refuses; `can_fast_forward` is true when a branch
    holds every commit the work tree is on; `fast_forward` moves the work tree to the tip of a
    branch with no commit and returns its short sha; `remove_worktree` and `delete_branch`
    remove the worktree and the branch, `delete_unmerged_branch` a branch whose commits the work
    tree does not hold. Each step raises GitError when git refuses it.
    """

    merge: Callable[[str], None]
    abort_merge: Callable[[], None]
    commit_merge: Callable[[str], str]
    commit_squash: Callable[[str], str]
    can_fast_forward: Callable[[str], bool]
    fast_forward: Callable[[str], str]
    remove_worktree: Callable[[Path], None]
    delete_branch: Callable[[str], None]
    delete_unmerged_branch: Callable[[str], None]


# The steps of a landing in a work tree built without them: each one refuses, as no such work
# tree lands.
NO_LANDING = LandingSteps(*([_lands_nothing] * 9))


@dataclass(frozen=True)
class WorkTree:
    """The git work tree a record is inside: its top and its steps, each bound to it.

    `commit_files` commits the files, relative to the top, alone with a message and returns the
    sha; `add_worktree` checks out a new branch at a commit in a new worktree at a path;
    `ignores` is true when a rule git reads names a path. `current_branch` names the branch the
    work tree is on, empty on none; `find_branches` lists the branches matching a pattern;
    `find_worktree` is the worktree of a branch, or None; `find_worktrees` lists every worktree
    of the repository. `landing` holds the steps only a landing takes. Each step raises GitError
    when git refuses it.
    """

    path: Path
    commit_files: Callable[[Sequence[Path], str], str]
    add_worktree: Callable[[str, Path, str], None]
    current_branch: Callable[[], str]
    find_branches: Callable[[str], list[str]]
    find_worktree: Callable[[str], Path | None]
    find_worktrees: Callable[[], list[Path]]
    ignores: Callable[[Path], bool] = _ignores_nothing
    landing: LandingSteps = NO_LANDING


# The git work tree the directory is inside, or None when it is inside none.
OpenGit = Callable[[Path], WorkTree | None]


@dataclass(frozen=True)
class Said:
    """What fgraph says of a command: its lines on the output, a warning on the error output."""

    out: str
    warning: str = ""


def open_git(directory: Path) -> WorkTree | None:
    """The git work tree the directory is inside, its steps run by git; None when in none."""
    top = branch.work_tree_of(directory)
    if top is None:
        return None
    return WorkTree(
        path=top,
        commit_files=partial(branch.commit_files, top),
        add_worktree=partial(branch.add_worktree, top),
        current_branch=partial(branch.current_branch, top),
        find_branches=partial(branch.branches_like, top),
        find_worktree=partial(branch.worktree_of_branch, top),
        find_worktrees=partial(branch.worktrees, top),
        ignores=partial(branch.ignores, top),
        landing=LandingSteps(
            merge=partial(branch.merge_uncommitted, top),
            abort_merge=partial(branch.abort_merge, top),
            commit_merge=partial(branch.commit_merge, top),
            commit_squash=partial(branch.commit_squash, top),
            can_fast_forward=partial(branch.can_fast_forward, top),
            fast_forward=partial(branch.fast_forward, top),
            remove_worktree=partial(branch.remove_worktree, top),
            delete_branch=partial(branch.delete_branch, top),
            delete_unmerged_branch=partial(branch.delete_unmerged_branch, top),
        ),
    )


def kept_in(record: Path, open_git: OpenGit) -> WorkTree | None:
    """The git work tree that keeps the record: None outside one, and None when git ignores it.

    No branch scopes the writes of a record no work tree keeps, and no worktree holds a copy.
    """
    work_tree = open_git(record)
    if work_tree is None or work_tree.ignores(record):
        return None
    return work_tree


def commit_written(
    written: Written, store: Store, record: Path, open_git: OpenGit, config: Config
) -> Said:
    """Commit the files the write changed under its message; what fgraph says of the write.

    Outside a git work tree nothing is committed, and only the start of a work item warns, that
    no branch was made. For a record git ignores nothing is committed either, and the branch of
    a start is checked out at HEAD. A write that changed no file makes no commit. With the
    development off in the configuration the start of a work item is a write as any other: no
    branch, no worktree and no warning. With the commits off in the configuration a write is
    left as that of a record git ignores. Raises GitError naming the git command when git refuses
    a step: a commit refused puts the files back as they were, a worktree refused leaves the
    start as it is, committed or written.
    """
    to_branch = written.branch if config.development.enabled else None
    work_tree = open_git(record)
    if work_tree is None:
        if to_branch is None:
            return Said(written.out)
        warning = f"fgraph: warning: no branch made: {record} is not inside a git work tree\n"
        return Said(written.out, warning)
    top = work_tree.path.resolve()
    if not config.git.commit or work_tree.ignores(record):
        at = HEAD
    else:
        files = [file.resolve().relative_to(top) for file in store.find_changed_files()]
        if not files:
            return Said(written.out)
        try:
            at = work_tree.commit_files(files, written.message)
        except GitError:
            store.restore_files()
            raise
    if to_branch is None:
        return Said(written.out)
    return Said(written.out + branch_started(to_branch, work_tree, at))


def branch_started(to_branch: ToBranch, work_tree: WorkTree, at: str = HEAD) -> str:
    """Check the branch of a started work item out at the commit, in a worktree of its own.

    Returns the line that names the branch and its worktree. Raises GitError when git refuses
    the worktree, naming the work item started, at the commit when it is one of the record.
    """
    made = branch_of(to_branch.item, to_branch.slug, work_tree.path.resolve())
    try:
        work_tree.add_worktree(made.name, made.path, at)
    except GitError as error:
        where = "" if at == HEAD else f" at {at[:7]}"
        started = f"{work_item_id_text(to_branch.item)} is started{where}"
        raise GitError(f"{error} -- {started}, its branch is not") from error
    return f"branch {made.name} in {made.path}\n"
