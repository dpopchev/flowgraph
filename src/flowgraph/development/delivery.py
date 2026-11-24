"""The delivery of a landing: the pushes of main and the tag, each refused with the way back.

`[delivery]` of the configuration says what a landing takes beside the merge: main pushed to the
branch it tracks, and main tagged with its version. Each step raises the GitError git gave it,
with the work item and the commit the landing came to, so a landing refused says how far it came.
A main that tracks no branch of a remote is refused by `check_main_tracked`, before any merge.
"""

from collections.abc import Callable

from flowgraph.development.branch import MAIN
from flowgraph.development.commit import WorkTree
from flowgraph.development.git import GitError
from flowgraph.development.way import LandError
from flowgraph.record import DELIVERY_PUSH


def check_main_tracked(item: str, work_tree: WorkTree) -> None:
    """Check main tracks a branch of a remote, before a landing that pushes its merges.

    Raises LandError naming the work item and the remote main lacks, when it tracks none; nothing
    is merged before the check.
    """
    try:
        work_tree.landing.upstream(MAIN)
    except GitError as error:
        raise LandError(
            f"{item} cannot land: {error} -- run git push --set-upstream <remote> {MAIN}, "
            f"or fgraph config set {DELIVERY_PUSH} false"
        ) from error


def pushed(item: str, sha: str, work_tree: WorkTree) -> None:
    """Push main once the landing is whole, to carry the write that completes the work item.

    Raises GitError saying the work item is landed and main is not pushed when git refuses it.
    """
    try:
        work_tree.landing.push(MAIN)
    except GitError as error:
        landed = f"{item} is landed at {sha}, {MAIN} is not pushed"
        raise GitError(f"{error} -- {landed}") from error


def pushed_at_merge(item: str, sha: str, work_tree: WorkTree) -> str:
    """Push main once the merge is made; the line that names the remote it is pushed to.

    Raises GitError saying main is not pushed, the work item merged and not completed, and that
    `fgraph land` run again takes it up, when git refuses it.
    """
    try:
        remote = work_tree.landing.push(MAIN)
    except GitError as error:
        raise GitError(f"{error} -- {MAIN} is not pushed -- {_merged(item, sha)}") from error
    return f"pushed {MAIN} to {remote}\n"


def tagged_at_merge(item: str, sha: str, tag: Callable[[], str]) -> str:
    """Tag main once the merge is made, before the write that completes; what the tag says.

    Raises GitError saying the work item is merged and not completed, and that `fgraph land` run
    again takes it up, when git refuses the tag or its push.
    """
    try:
        return tag()
    except GitError as error:
        raise GitError(f"{error} -- {_merged(item, sha)}") from error


def _merged(item: str, sha: str) -> str:
    """The way back of a landing refused after its merge: it is not completed, land it again."""
    return f"{item} is merged at {sha} and not completed -- run fgraph land {item} again"
