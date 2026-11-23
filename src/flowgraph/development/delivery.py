"""The delivery of a landing: the pushes of main and the tag, each refused with the way back.

`[delivery]` of the configuration says what a landing takes beside the merge: main pushed to the
branch it tracks, and main tagged with its version. Each step raises the GitError git gave it,
with the work item and the commit the landing came to, so a landing refused says how far it came.
"""

from collections.abc import Callable

from flowgraph.development.branch import MAIN
from flowgraph.development.commit import Said, WorkTree
from flowgraph.development.git import GitError
from flowgraph.development.release import ReleaseError
from flowgraph.item.commands import Written
from flowgraph.parent import FeatureId, feature_id_text
from flowgraph.record import Config
from flowgraph.record.layers import TagAt


def pushed(item: str, sha: str, work_tree: WorkTree, untagged: FeatureId | None) -> None:
    """Push main once the landing is whole, to carry the write that completes the work item.

    Raises GitError saying the work item is landed and main is not pushed when git refuses it,
    and that the Feature is not tagged when the landing completes one it was to tag.
    """
    try:
        work_tree.landing.push(MAIN)
    except GitError as error:
        landed = f"{item} is landed at {sha}, {MAIN} is not pushed"
        if untagged is not None:
            landed += f", {feature_id_text(untagged)} is not tagged"
        raise GitError(f"{error} -- {landed}") from error


def pushed_at_merge(item: str, sha: str, work_tree: WorkTree) -> str:
    """Push main once the merge is made; the line that names the remote it is pushed to.

    Raises GitError saying main is not pushed, the work item merged and not completed, and that
    `fgraph land` run again takes it up, when git refuses it.
    """
    try:
        remote = work_tree.landing.push(MAIN)
    except GitError as error:
        merged = f"{item} is merged at {sha} and not completed -- run fgraph land {item} again"
        raise GitError(f"{error} -- {MAIN} is not pushed -- {merged}") from error
    return f"pushed {MAIN} to {remote}\n"


def to_tag(config: Config, written: Written) -> FeatureId | None:
    """The Feature whose close a landing tags main at; None when it tags nothing.

    It is the Feature the write of the landing completes, under `delivery.tag` feature-close.
    """
    return written.completes if config.delivery.tag is TagAt.FEATURE_CLOSE else None


def tagged(item: str, sha: str, feature: FeatureId, release: Callable[[], Said]) -> str:
    """Tag main as `fgraph release` does, once the landing is whole; what the release says.

    Raises the refusal of the release saying the work item is landed and the Feature completed.
    """
    try:
        return release().out
    except (GitError, ReleaseError) as error:
        completed = f"{item} is landed at {sha}, {feature_id_text(feature)} is completed"
        raise type(error)(f"{error} -- {completed}") from error
