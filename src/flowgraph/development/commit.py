"""The commit of a write of the record: fgraph commits the files the write changed, alone.

Every write shares this one step. With the development on and the mode branch, not the trunk,
the start of a work item also checks its branch out at that commit, in a worktree of its own.
Outside a git work tree a write is left as its files, and so is the write of a record git
ignores, whose start branches at HEAD, and every write of a record whose configuration turns
the commits off. The steps only a landing and only a release take are held in
flowgraph.development.steps.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from flowgraph.development import git, history_git, pull_git, tag_git, uncommitted_git
from flowgraph.development.branch import branch_of
from flowgraph.development.git import GitError
from flowgraph.development.steps import NO_LANDING, NO_RELEASE, LandingSteps, ReleaseSteps
from flowgraph.item.commands import ToBranch, Written
from flowgraph.record import Config, branched
from flowgraph.record.store import Store
from flowgraph.work_item import work_item_id_text

# Where the branch of a start is checked out when the write of the record made no commit.
HEAD = "HEAD"


def _ignores_nothing(path: Path) -> bool:
    """The `ignores` of a work tree built without it: git ignores no path there."""
    return False


def _knows_no_commit(commit: str) -> None:
    """The `changed_files` of a work tree built without it: it knows no commit."""
    return None


def _touches_no_path(path: str) -> bool:
    """The `touched_path` of a work tree built without it: no commit touched a path."""
    return False


def _lists_no_change() -> list[str]:
    """The `uncommitted_files` of a work tree built without it: it lists no file."""
    return []


@dataclass(frozen=True)
class WorkTree:
    """The git work tree a record is inside: its top and its steps, each bound to it.

    `commit_files` commits the files, relative to the top, alone with a message and returns the
    sha; `add_worktree` checks out a new branch at a commit in a new worktree at a path;
    `ignores` is true when a rule git reads names a path. `current_branch` names the branch the
    work tree is on, empty on none; `find_branches` lists the branches matching a pattern;
    `find_worktree` is the worktree of a branch, or None; `find_worktrees` lists every worktree
    of the repository. `changed_files` lists the files a commit changed, as paths from the top, a
    merge commit by what it brought to its first parent, and answers None for a sha git does not
    know. `touched_path` is true when a commit of the history of HEAD changed the file at a path
    from the top, a deleted file too. `uncommitted_files` lists the files changed in the work
    tree and not committed, as paths from the top. `landing` holds the steps only a landing
    takes, `release` those only a release takes. Each step raises GitError when git refuses it.
    """

    path: Path
    commit_files: Callable[[Sequence[Path], str], str]
    add_worktree: Callable[[str, Path, str], None]
    current_branch: Callable[[], str]
    find_branches: Callable[[str], list[str]]
    find_worktree: Callable[[str], Path | None]
    find_worktrees: Callable[[], list[Path]]
    ignores: Callable[[Path], bool] = _ignores_nothing
    changed_files: Callable[[str], list[str] | None] = _knows_no_commit
    uncommitted_files: Callable[[], list[str]] = _lists_no_change
    landing: LandingSteps = NO_LANDING
    release: ReleaseSteps = NO_RELEASE
    touched_path: Callable[[str], bool] = _touches_no_path


# The git work tree the directory is inside, or None when it is inside none.
OpenGit = Callable[[Path], WorkTree | None]


@dataclass(frozen=True)
class Said:
    """What fgraph says of a command: its lines on the output, a warning on the error output."""

    out: str
    warning: str = ""


def open_git(directory: Path) -> WorkTree | None:
    """The git work tree the directory is inside, its steps run by git; None when in none."""
    top = git.work_tree_of(directory)
    if top is None:
        return None
    return WorkTree(
        path=top,
        commit_files=partial(git.commit_files, top),
        add_worktree=partial(git.add_worktree, top),
        current_branch=partial(git.current_branch, top),
        find_branches=partial(git.branches_like, top),
        find_worktree=partial(git.worktree_of_branch, top),
        find_worktrees=partial(git.worktrees, top),
        ignores=partial(git.ignores, top),
        changed_files=partial(git.changed_files, top),
        uncommitted_files=partial(uncommitted_git.uncommitted_files, top),
        landing=LandingSteps(
            merge=partial(git.merge_uncommitted, top),
            abort_merge=partial(git.abort_merge, top),
            commit_merge=partial(git.commit_merge, top),
            commit_squash=partial(git.commit_squash, top),
            can_fast_forward=partial(git.can_fast_forward, top),
            fast_forward=partial(git.fast_forward, top),
            remove_worktree=partial(git.remove_worktree, top),
            delete_branch=partial(git.delete_branch, top),
            delete_unmerged_branch=partial(git.delete_unmerged_branch, top),
            push=partial(git.push, top),
            upstream=partial(git.upstream_of, top),
            publish=partial(pull_git.push_beside, top),
        ),
        release=ReleaseSteps(
            find_tags=partial(tag_git.tags_like, top),
            holds_commit=partial(tag_git.holds_commit, top),
            tagged_at=partial(tag_git.tagged_at, top),
            make_tag=partial(tag_git.make_tag, top),
            push_tag=partial(tag_git.push_tag, top),
        ),
        touched_path=partial(history_git.touched_path, top),
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
    development off or on the trunk the start of a work item is a write as any other: no
    branch, no worktree and no warning. With the commits off in the configuration a write is
    left as that of a record git ignores. Raises GitError naming the git command when git refuses
    a step: a commit refused puts the files back as they were, a worktree refused leaves the
    start as it is, committed or written.
    """
    to_branch = written.branch if branched(config.development) else None
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
