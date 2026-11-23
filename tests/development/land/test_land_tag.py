"""The tag at the close of a Feature: a landing that completes one tags main, with fakes.

Under `delivery.tag` feature-close the landing that completes a Feature is followed by the tag
`fgraph release` makes, pushed after main under `delivery.push`; any other landing tags nothing.
"""

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Never

import pytest

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.development import GitError
from flowgraph.development.commit import LandingSteps, ReleaseSteps, Said, WorkTree
from flowgraph.development.land import land_item
from flowgraph.feature import FeatureState, make_feature, started_feature
from flowgraph.parent import STANDALONE, FeatureId, Parent, make_feature_id
from flowgraph.record import Config, make_config
from flowgraph.record.queue import make_queue
from flowgraph.record.store import FeatureStore, Store
from flowgraph.story import STORY as STORY_KIND
from flowgraph.story import make_story, make_story_id
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    Kind,
    WorkItemId,
    WorkItemRow,
    WorkItemState,
    append_task,
    completed_task,
    started_task,
    started_work_item,
    work_item_row,
)

pytestmark = pytest.mark.command

ENABLED = "[development]\nenabled = true\n"
FEATURE_CLOSE = '[delivery]\ntag = "feature-close"\n'
TAGGED = make_config(f"{ENABLED}{FEATURE_CLOSE}")
TAGGED_AND_PUSHED = make_config(f"{ENABLED}{FEATURE_CLOSE}push = true\n")
UNTAGGED = make_config(f'{ENABLED}[delivery]\ntag = "none"\n')
TOP = Path("/src/project")
RECORD = TOP / ".fgraph"
FILE = RECORD / "items" / "S-0001.toml"
BRANCH = "wi/S-0001-a-slug"
WORKTREE = Path("/src/project.worktrees/S-0001-a-slug")
CREATED = datetime(2026, 1, 1, tzinfo=UTC)
NOW = datetime(2026, 1, 3, tzinfo=UTC)
F1 = make_feature_id(1)
FEATURE = started_feature(
    make_feature(F1, "a feature title", ["a criterion"], "", CREATED), CREATED
)
MESSAGE = "feat: land the last Story"
MERGE = "3e9ae5c"
HEAD = "4c2e1d0"
LANDED = f"landed S-0001 at {MERGE}\ncompleted F-0001 at {MERGE}\n"
TAG_MADE = ("tag", "v0.1.0", "release v0.1.0", "main")


def never(*_: object) -> Never:
    """A read, a write or a git step that a landing never asks for."""
    raise AssertionError("a landing never asks for this")


def refuse(*_: object) -> Never:
    """A git step that git refuses."""
    raise GitError("git failed: refused")


def ready(parent: Parent) -> WorkItemState:
    """S-0001 under that parent, started, its one Task completed: ready to land."""
    task = make_task(make_task_id(1), "a task", "an output", "", CREATED)
    story = make_story(make_story_id(1), "a title", make_scenario("a", "b", "c"), "", CREATED)
    opened = started_work_item(append_task(replace(story, parent=parent), task), NOW)
    begun = started_task(opened, make_task_id(1), NOW)
    return completed_task(begun, make_task_id(1), NOW, make_commit("abc1234"))


def store(parent: Parent) -> Store:
    """The store of a record holding S-0001 under that parent and the started Feature F-0001.

    It reads back what it saved, so the release that follows a landing finds S-0001 completed.
    """
    held: dict[WorkItemId, WorkItemState] = {make_story_id(1): ready(parent)}
    features: dict[FeatureId, FeatureState] = {F1: FEATURE}

    def save_feature(feature: FeatureState) -> None:
        features[feature.id] = feature

    def find_rows(kind: Kind) -> list[WorkItemRow]:
        return [work_item_row(item) for item in held.values()] if kind == STORY_KIND else []

    return Store(
        find_work_item_rows=find_rows,
        load_work_item=held.__getitem__,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=lambda item: held.__setitem__(item.id, item),
        load_queue=lambda: make_queue([]),
        save_queue=never,
        find_changed_files=lambda: [FILE],
        restore_files=lambda: None,
        features=FeatureStore(features.__getitem__, save_feature, lambda: ["F-0001"]),
    )


def work_tree(steps: list[object]) -> WorkTree:
    """A work tree at TOP on main holding BRANCH in WORKTREE, with no tag; it notes each step."""

    def make_tag(tag: str, message: str, branch: str) -> str:
        steps.append(("tag", tag, message, branch))
        return HEAD

    def push_tag(branch: str, tag: str) -> str:
        steps.append(("push tag", branch, tag))
        return "origin"

    def push(branch: str) -> str:
        steps.append(("push", branch))
        return "origin"

    def commit_files(files: Sequence[Path], message: str) -> str:
        steps.append(("commit", message))
        return HEAD

    return WorkTree(
        path=TOP,
        commit_files=commit_files,
        add_worktree=never,
        current_branch=lambda: "main",
        find_branches=lambda _: [BRANCH],
        find_worktree=lambda _: WORKTREE,
        find_worktrees=never,
        landing=LandingSteps(
            merge=lambda branch: steps.append(("merge", branch)),
            abort_merge=never,
            commit_merge=lambda _: MERGE,
            commit_squash=never,
            can_fast_forward=never,
            fast_forward=never,
            remove_worktree=lambda _: None,
            delete_branch=lambda _: None,
            delete_unmerged_branch=never,
            push=push,
        ),
        release=ReleaseSteps(
            find_tags=lambda _: [],
            holds_commit=never,
            tagged_at=never,
            make_tag=make_tag,
            push_tag=push_tag,
        ),
    )


def land(tree: WorkTree, config: Config = TAGGED, parent: Parent = F1) -> Said:
    """Land S-0001 under that parent in the work tree, the development on."""
    kept = store(parent)
    return land_item("S-0001", MESSAGE, kept, lambda: NOW, RECORD, lambda _: tree, config, never)


def test_a_landing_that_completes_a_feature_names_the_tag_after_the_feature() -> None:
    assert land(work_tree([])) == Said(f"{LANDED}tagged v0.1.0 at {HEAD}\n")


def test_a_landing_that_completes_a_feature_tags_the_head_of_main_once_it_is_committed() -> None:
    steps: list[object] = []
    land(work_tree(steps))
    assert steps[-2:] == [("commit", "chore: complete S-0001 and F-0001 in the record"), TAG_MADE]


def test_a_landing_that_completes_a_feature_with_the_push_pushes_main_then_the_tag() -> None:
    steps: list[object] = []
    land(work_tree(steps), TAGGED_AND_PUSHED)
    assert steps[-3:] == [("push", "main"), TAG_MADE, ("push tag", "main", "v0.1.0")]


def test_a_landing_that_completes_a_feature_with_the_push_names_both_pushes() -> None:
    assert land(work_tree([]), TAGGED_AND_PUSHED) == Said(
        f"{LANDED}pushed main to origin\ntagged v0.1.0 at {HEAD}\npushed v0.1.0 to origin\n"
    )


@pytest.mark.parametrize(
    ("config", "parent"),
    [(UNTAGGED, F1), (make_config(ENABLED), F1), (TAGGED, STANDALONE)],
    ids=["delivery-tag-none", "delivery-tag-left-out", "a-work-item-standing-alone"],
)
def test_a_landing_tags_nothing_unless_it_completes_a_feature_under_feature_close(
    config: Config, parent: Parent
) -> None:
    steps: list[object] = []
    land(work_tree(steps), config, parent)
    assert TAG_MADE not in steps


def test_a_tag_git_refuses_says_the_work_item_is_landed_and_the_feature_completed() -> None:
    tree = work_tree([])
    refused = replace(tree, release=replace(tree.release, make_tag=refuse))
    with pytest.raises(GitError) as error:
        land(refused)
    assert str(error.value) == (
        f"git failed: refused -- S-0001 is landed at {MERGE}, F-0001 is completed"
    )


def test_a_push_of_the_tag_git_refuses_says_the_tag_is_made_and_not_pushed() -> None:
    tree = work_tree([])
    refused = replace(tree, release=replace(tree.release, push_tag=refuse))
    with pytest.raises(GitError) as error:
        land(refused, TAGGED_AND_PUSHED)
    assert str(error.value) == (
        f"git failed: refused -- v0.1.0 is tagged at {HEAD}, it is not pushed"
        f" -- S-0001 is landed at {MERGE}, F-0001 is completed"
    )


def test_a_push_of_main_git_refuses_says_the_feature_is_not_tagged() -> None:
    tree = work_tree([])
    refused = replace(tree, landing=replace(tree.landing, push=refuse))
    with pytest.raises(GitError) as error:
        land(refused, TAGGED_AND_PUSHED)
    assert str(error.value) == (
        f"git failed: refused -- S-0001 is landed at {MERGE}, main is not pushed"
        ", F-0001 is not tagged"
    )


def test_a_push_of_main_git_refuses_makes_no_tag() -> None:
    steps: list[object] = []
    tree = work_tree(steps)
    refused = replace(tree, landing=replace(tree.landing, push=refuse))
    with pytest.raises(GitError):
        land(refused, TAGGED_AND_PUSHED)
    assert TAG_MADE not in steps
