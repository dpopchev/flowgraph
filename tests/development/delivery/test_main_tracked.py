"""The check of a landing: main must track a branch of a remote before the merge of a push."""

import re
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Never

import pytest

from flowgraph.development.branch import MAIN
from flowgraph.development.commit import NO_LANDING, WorkTree
from flowgraph.development.delivery import check_main_tracked
from flowgraph.development.git import GitError
from flowgraph.development.way import LandError
from flowgraph.record import DELIVERY_PUSH

pytestmark = pytest.mark.command

ITEM = "S-0001"
LINE = (
    f"{ITEM} cannot land: main tracks no branch of a remote to push to -- "
    f"run git push --set-upstream <remote> {MAIN}, or fgraph config set {DELIVERY_PUSH} false"
)


def _never(*_: object) -> Never:
    """A step the check never takes: it asks only the upstream of the landing."""
    raise AssertionError("the check takes no step but the upstream of the landing")


def work_tree(upstream: Callable[[str], tuple[str, str]]) -> WorkTree:
    """A work tree whose every step is a contract, but its landing's upstream step."""
    return WorkTree(
        path=Path("/project"),
        commit_files=_never,
        add_worktree=_never,
        current_branch=_never,
        find_branches=_never,
        find_worktree=_never,
        find_worktrees=_never,
        landing=replace(NO_LANDING, upstream=upstream),
    )


def tracks_origin(branch: str) -> tuple[str, str]:
    """The upstream of a main that tracks the origin."""
    return ("origin", "refs/heads/main")


def tracks_no_remote(branch: str) -> tuple[str, str]:
    """The upstream of a main that tracks no branch of a remote."""
    raise GitError(f"{MAIN} tracks no branch of a remote to push to")


def test_a_main_that_tracks_a_branch_passes_the_check() -> None:
    assert check_main_tracked(ITEM, work_tree(tracks_origin)) is None


def test_a_main_that_tracks_no_branch_is_refused_with_the_whole_line() -> None:
    with pytest.raises(LandError, match=f"^{re.escape(LINE)}$"):
        check_main_tracked(ITEM, work_tree(tracks_no_remote))


def test_the_check_asks_the_upstream_of_main_alone() -> None:
    asked: list[str] = []

    def upstream(branch: str) -> tuple[str, str]:
        asked.append(branch)
        return tracks_origin(branch)

    check_main_tracked(ITEM, work_tree(upstream))
    assert asked == [MAIN]
