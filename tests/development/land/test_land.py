"""The landing of a work item: its git steps in order and what it refuses, with fakes."""

from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Never

import pytest

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.development import GateError, GitError, RunGate
from flowgraph.development.commit import LandingSteps, Said, WorkTree
from flowgraph.development.land import LandError, land_item
from flowgraph.feature import FeatureNotFoundError, make_feature, started_feature
from flowgraph.item import Store
from flowgraph.parent import FeatureId, make_feature_id
from flowgraph.record import Config, make_config
from flowgraph.record.queue import make_queue
from flowgraph.record.store import FeatureStore
from flowgraph.story import STORY as STORY_KIND
from flowgraph.story import make_story, make_story_id
from flowgraph.task import OpenTaskError, make_task, make_task_id
from flowgraph.work_item import (
    CompletedWorkItem,
    WorkItemState,
    append_task,
    completed_task,
    started_task,
    started_work_item,
    work_item_row,
)

pytestmark = pytest.mark.command

ON = make_config("[development]\nenabled = true\n")
OFF = make_config("")
SQUASH = make_config('[development]\nenabled = true\nmerge = "squash"\n')
FAST_FORWARD = make_config('[development]\nenabled = true\nmerge = "fast-forward"\n')
GATE = 'gate = "make check"\n'
GATED = make_config(f"[development]\nenabled = true\n{GATE}")
GATED_SQUASH = make_config(f'[development]\nenabled = true\nmerge = "squash"\n{GATE}')
GATED_FAST_FORWARD = make_config(f'[development]\nenabled = true\nmerge = "fast-forward"\n{GATE}')
WAYS = ["merge-commit", "squash", "fast-forward"]
RECORD_COMMIT = ("commit", [".fgraph/items/S-0001.toml"], "chore: complete S-0001 in the record")
TOP = Path("/src/project")
RECORD = TOP / ".fgraph"
FILE = RECORD / "items" / "S-0001.toml"
BRANCH = "wi/S-0001-a-slug"
WORKTREE = Path("/src/project.worktrees/S-0001-a-slug")
NEXT_BRANCH = "wi/S-0002-another-title"
NEXT_WORKTREE = Path("/src/project.worktrees/S-0002-another-title")
CREATED = datetime(2026, 1, 1, tzinfo=UTC)
NOW = datetime(2026, 1, 3, tzinfo=UTC)
TASK = make_task(make_task_id(1), "a task", "an output", "", CREATED)
STORY = make_story(make_story_id(1), "a title", make_scenario("a", "b", "c"), "", CREATED)
OPEN = started_task(started_work_item(append_task(STORY, TASK), NOW), make_task_id(1), NOW)
READY = completed_task(OPEN, make_task_id(1), NOW, make_commit("abc1234"))
MESSAGE = "feat: land the first Story"
GATE_RUN = ("gate", "make check", TOP)


def never(*_: object) -> Never:
    """A read or a write of the record that a landing never asks for."""
    raise AssertionError("a landing loads the work item, saves it and names its file")


def refuse(*_: object) -> Never:
    """A git step that git refuses."""
    raise GitError("git failed: refused")


def store(item: WorkItemState, saved: list[WorkItemState] | None = None) -> Store:
    """The store of a record holding that work item, whose save changes its file."""
    kept = [] if saved is None else saved
    return Store(
        find_work_item_rows=never,
        load_work_item=lambda _: item,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=kept.append,
        load_queue=never,
        save_queue=never,
        find_changed_files=lambda: [FILE],
        restore_files=lambda: None,
    )


def work_tree(steps: list[object]) -> WorkTree:
    """A work tree at TOP on main holding BRANCH in WORKTREE; it notes each step it takes."""

    def commit_files(files: Sequence[Path], message: str) -> str:
        steps.append(("commit", [str(file) for file in files], message))
        return "0000000"

    def commit_merge(message: str) -> str:
        steps.append(("commit merge", message))
        return "3e9ae5c"

    def commit_squash(message: str) -> str:
        steps.append(("commit squash", message))
        return "5d1e0aa"

    def fast_forward(branch: str) -> str:
        steps.append(("fast-forward", branch))
        return "9f8e7d6"

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
            abort_merge=lambda: steps.append("abort merge"),
            commit_merge=commit_merge,
            commit_squash=commit_squash,
            can_fast_forward=lambda _: True,
            fast_forward=fast_forward,
            remove_worktree=lambda path: steps.append(("remove worktree", path)),
            delete_branch=lambda branch: steps.append(("delete branch", branch)),
            delete_unmerged_branch=lambda branch: steps.append(("delete unmerged branch", branch)),
        ),
    )


def with_step(tree: WorkTree, **steps: Callable[..., object]) -> WorkTree:
    """The work tree with those steps of its landing in place of its own."""
    return replace(tree, landing=replace(tree.landing, **steps))


def no_gate(*_: object) -> Never:
    """The gate of a record that names none: a landing never runs it."""
    raise AssertionError("a landing under no gate runs none")


def gate(steps: list[object], status: int = 0) -> RunGate:
    """A gate that exits with that status; it notes the command it runs and where."""

    def run(command: str, directory: Path) -> int:
        steps.append(("gate", command, directory))
        return status

    return run


def land(
    item: WorkItemState,
    tree: WorkTree | None,
    saved: list[WorkItemState] | None = None,
    config: Config = ON,
    message: str | None = MESSAGE,
    run_gate: RunGate = no_gate,
) -> Said:
    """Land S-0001 on the record holding that work item, in that work tree, the development on."""
    kept = store(item, saved)
    return land_item("S-0001", message, kept, lambda: NOW, RECORD, lambda _: tree, config, run_gate)


def test_a_landing_with_the_development_off_is_refused_naming_the_key() -> None:
    with pytest.raises(LandError) as error:
        land(READY, work_tree([]), config=OFF)
    assert str(error.value) == (
        "S-0001 cannot land: the development is off"
        " -- run fgraph config set development.enabled true"
    )


def test_a_landing_with_the_commits_off_is_refused_naming_both_keys() -> None:
    with pytest.raises(LandError) as error:
        land(READY, work_tree([]), config=make_config("[git]\ncommit = false\n"))
    assert str(error.value) == (
        "S-0001 cannot land: the development is off -- run fgraph config set git.commit true,"
        " then fgraph config set development.enabled true"
    )


def test_a_landing_with_the_development_off_takes_no_git_step() -> None:
    steps: list[object] = []
    with pytest.raises(LandError):
        land(READY, work_tree(steps), config=OFF)
    assert steps == []


def test_a_landing_takes_its_git_steps_in_order() -> None:
    steps: list[object] = []
    land(READY, work_tree(steps))
    assert steps == [
        ("merge", BRANCH),
        ("commit merge", MESSAGE),
        ("commit", [".fgraph/items/S-0001.toml"], "chore: complete S-0001 in the record"),
        ("remove worktree", WORKTREE),
        ("delete branch", BRANCH),
    ]


def test_a_landing_names_the_work_item_and_the_merge_commit() -> None:
    assert land(READY, work_tree([])) == Said("landed S-0001 at 3e9ae5c\n")


def test_a_landing_completes_the_work_item_at_the_merge_commit() -> None:
    saved: list[WorkItemState] = []
    land(READY, work_tree([]), saved)
    assert [(type(item), item.commit) for item in saved if isinstance(item, CompletedWorkItem)] == [
        (CompletedWorkItem, make_commit("3e9ae5c"))
    ]


def last_of_a_started_feature() -> Store:
    """The store of a record whose started Feature F-0001 holds S-0001 alone, ready to land."""
    last = replace(READY, parent=make_feature_id(1))
    feature = make_feature(make_feature_id(1), "a feature title", ["a criterion"], "", CREATED)
    started = started_feature(feature, CREATED)
    return replace(
        store(last),
        find_work_item_rows=lambda kind: [work_item_row(last)] if kind == STORY_KIND else [],
        load_queue=lambda: make_queue([]),
        features=FeatureStore(lambda _: started, lambda _: None, lambda: ["F-0001"]),
    )


def test_a_landing_that_completes_the_feature_of_the_work_item_names_it_after_the_work_item() -> (
    None
):
    kept, tree = last_of_a_started_feature(), work_tree([])
    landed = land_item("S-0001", MESSAGE, kept, lambda: NOW, RECORD, lambda _: tree, ON, no_gate)
    assert landed == Said("landed S-0001 at 3e9ae5c\ncompleted F-0001 at 3e9ae5c\n")


def test_a_landing_that_completes_the_feature_commits_the_record_once_naming_both() -> None:
    steps: list[object] = []
    kept, tree = last_of_a_started_feature(), work_tree(steps)
    land_item("S-0001", MESSAGE, kept, lambda: NOW, RECORD, lambda _: tree, ON, no_gate)
    assert steps[2] == (
        "commit",
        [".fgraph/items/S-0001.toml"],
        "chore: complete S-0001 and F-0001 in the record",
    )


def test_a_landing_under_a_feature_the_record_does_not_hold_drops_the_merge_before_main_moves() -> (
    None
):
    def lacking(feature_id: FeatureId) -> Never:
        raise FeatureNotFoundError(feature_id)

    steps: list[object] = []
    kept = replace(
        last_of_a_started_feature(),
        features=FeatureStore(lacking, never, lambda: []),
    )
    with pytest.raises(FeatureNotFoundError):
        land_item(
            "S-0001", MESSAGE, kept, lambda: NOW, RECORD, lambda _: work_tree(steps), ON, no_gate
        )
    assert steps == [("merge", BRANCH), "abort merge"]


def first_of_a_started_feature() -> Store:
    """The store of a record whose started Feature F-0001 holds S-0001 ready and S-0002 in Backlog.

    S-0002 has one Task; the store reads back the work items it saves.
    """
    under = make_feature_id(1)
    second = make_story(make_story_id(2), "another title", make_scenario("a", "b", "c"), "", NOW)
    task = make_task(make_task_id(2), "a task", "an output", "", NOW)
    items = [replace(READY, parent=under), replace(append_task(second, task), parent=under)]
    held = {item.id: item for item in items}
    feature = make_feature(under, "a feature title", ["a criterion"], "", CREATED)
    started = started_feature(feature, CREATED)
    return replace(
        store(READY),
        find_work_item_rows=lambda kind: (
            [work_item_row(item) for item in held.values()] if kind == STORY_KIND else []
        ),
        load_work_item=held.__getitem__,
        save_work_item=lambda item: held.update({item.id: item}),
        load_queue=lambda: make_queue([]),
        features=FeatureStore(lambda _: started, lambda _: None, lambda: ["F-0001"]),
    )


def branching(steps: list[object]) -> WorkTree:
    """The work tree of `work_tree` that also notes the worktree it adds for a branch."""

    def add_worktree(name: str, path: Path, at: str) -> None:
        steps.append(("add worktree", name, path, at))

    return replace(work_tree(steps), add_worktree=add_worktree)


def land_first(tree: WorkTree) -> Said:
    """Land S-0001, the first work item of the started Feature of `first_of_a_started_feature`."""
    kept = first_of_a_started_feature()
    return land_item("S-0001", MESSAGE, kept, lambda: NOW, RECORD, lambda _: tree, ON, no_gate)


def test_a_landing_that_starts_the_next_work_item_names_it_and_its_branch_after_the_work_item() -> (
    None
):
    assert land_first(branching([])) == Said(
        f"landed S-0001 at 3e9ae5c\nstarted S-0002\nbranch {NEXT_BRANCH} in {NEXT_WORKTREE}\n"
    )


def test_a_landing_branches_the_next_work_item_at_the_commit_of_the_record_once_it_is_done() -> (
    None
):
    steps: list[object] = []
    land_first(branching(steps))
    assert steps[2:] == [
        (
            "commit",
            [".fgraph/items/S-0001.toml"],
            "chore: complete S-0001 and start S-0002 in the record",
        ),
        ("remove worktree", WORKTREE),
        ("delete branch", BRANCH),
        ("add worktree", NEXT_BRANCH, NEXT_WORKTREE, "HEAD"),
    ]


def test_a_worktree_git_refuses_to_add_says_the_next_work_item_is_started_without_its_branch() -> (
    None
):
    with pytest.raises(
        GitError, match=r"^git failed: refused -- S-0002 is started, its branch is not$"
    ):
        land_first(replace(work_tree([]), add_worktree=refuse))


def test_a_worktree_git_refuses_to_remove_says_the_next_work_item_has_no_branch_either() -> None:
    with pytest.raises(
        GitError,
        match=r"^git failed: refused -- S-0001 is landed at 3e9ae5c, its worktree and its branch"
        r" are not removed; S-0002 is started, its branch is not$",
    ):
        land_first(with_step(branching([]), remove_worktree=refuse))


def test_a_branch_without_a_worktree_is_deleted_alone() -> None:
    steps: list[object] = []
    land(READY, replace(work_tree(steps), find_worktree=lambda _: None))
    assert steps[-2:] == [
        ("commit", [".fgraph/items/S-0001.toml"], "chore: complete S-0001 in the record"),
        ("delete branch", BRANCH),
    ]


def test_a_landing_with_a_task_not_completed_aborts_the_merge() -> None:
    steps: list[object] = []
    with pytest.raises(OpenTaskError):
        land(OPEN, work_tree(steps))
    assert steps == [("merge", BRANCH), "abort merge"]


def test_a_merge_commit_git_refuses_aborts_the_merge() -> None:
    steps: list[object] = []
    with pytest.raises(GitError):
        land(READY, with_step(work_tree(steps), commit_merge=refuse))
    assert steps == [("merge", BRANCH), "abort merge"]


def test_a_merge_git_refuses_takes_no_other_step() -> None:
    steps: list[object] = []
    with pytest.raises(GitError):
        land(READY, with_step(work_tree(steps), merge=refuse))
    assert steps == []


def test_a_landing_outside_a_git_work_tree_is_refused() -> None:
    with pytest.raises(
        LandError,
        match=r"^S-0001 cannot land: /src/project/.fgraph is not inside a git work tree$",
    ):
        land(READY, None)


def test_a_landing_on_a_record_git_ignores_takes_its_git_steps_but_the_commit_of_the_record() -> (
    None
):
    steps: list[object] = []
    land(READY, replace(work_tree(steps), ignores=lambda path: path == RECORD))
    assert steps == [
        ("merge", BRANCH),
        ("commit merge", MESSAGE),
        ("remove worktree", WORKTREE),
        ("delete branch", BRANCH),
    ]


def test_a_landing_on_a_record_git_ignores_completes_the_work_item_at_the_merge_commit() -> None:
    saved: list[WorkItemState] = []
    land(READY, replace(work_tree([]), ignores=lambda _: True), saved)
    assert [item.commit for item in saved if isinstance(item, CompletedWorkItem)] == [
        make_commit("3e9ae5c")
    ]


def test_a_landing_in_a_work_tree_that_is_not_on_main_is_refused() -> None:
    off_main = replace(work_tree([]), current_branch=lambda: BRANCH)
    with pytest.raises(LandError, match=rf"^S-0001 lands on main: /src/project is on {BRANCH}$"):
        land(READY, off_main)


def test_a_landing_without_a_branch_is_refused() -> None:
    with pytest.raises(LandError, match=r"^S-0001 has no branch wi/S-0001-\* to land$"):
        land(READY, replace(work_tree([]), find_branches=lambda _: []))


def test_a_landing_with_several_branches_is_refused_naming_them() -> None:
    two = replace(work_tree([]), find_branches=lambda _: [BRANCH, "wi/S-0001-other"])
    with pytest.raises(
        LandError, match=rf"^S-0001 has several branches to land: {BRANCH}, wi/S-0001-other$"
    ):
        land(READY, two)


def test_a_worktree_git_refuses_to_remove_says_the_work_item_is_landed() -> None:
    with pytest.raises(
        GitError,
        match=r"^git failed: refused -- S-0001 is landed at 3e9ae5c,"
        r" its worktree and its branch are not removed$",
    ):
        land(READY, with_step(work_tree([]), remove_worktree=refuse))


@pytest.mark.parametrize(
    ("config", "word"), [(ON, "merge-commit"), (SQUASH, "squash")], ids=["merge-commit", "squash"]
)
def test_a_landing_that_makes_a_commit_is_refused_without_a_message_naming_the_key(
    config: Config, word: str
) -> None:
    with pytest.raises(LandError) as error:
        land(READY, work_tree([]), config=config, message=None)
    assert str(error.value) == (
        f"S-0001 cannot land without --message: development.merge = {word} makes a commit to word"
    )


@pytest.mark.parametrize("config", [ON, SQUASH], ids=["merge-commit", "squash"])
def test_a_landing_refused_without_a_message_takes_no_git_step(config: Config) -> None:
    steps: list[object] = []
    with pytest.raises(LandError):
        land(READY, work_tree(steps), config=config, message=None)
    assert steps == []


def test_a_landing_by_squash_takes_its_git_steps_in_order() -> None:
    steps: list[object] = []
    land(READY, work_tree(steps), config=SQUASH)
    assert steps == [
        ("merge", BRANCH),
        ("commit squash", MESSAGE),
        RECORD_COMMIT,
        ("remove worktree", WORKTREE),
        ("delete unmerged branch", BRANCH),
    ]


def test_a_landing_by_squash_names_the_work_item_and_the_squash_commit() -> None:
    assert land(READY, work_tree([]), config=SQUASH) == Said("landed S-0001 at 5d1e0aa\n")


def test_a_landing_by_squash_completes_the_work_item_at_the_squash_commit() -> None:
    saved: list[WorkItemState] = []
    land(READY, work_tree([]), saved, SQUASH)
    assert [item.commit for item in saved if isinstance(item, CompletedWorkItem)] == [
        make_commit("5d1e0aa")
    ]


def test_a_landing_by_squash_with_a_task_not_completed_aborts_the_merge() -> None:
    steps: list[object] = []
    with pytest.raises(OpenTaskError):
        land(OPEN, work_tree(steps), config=SQUASH)
    assert steps == [("merge", BRANCH), "abort merge"]


def test_a_squash_commit_git_refuses_takes_no_step_of_the_record() -> None:
    steps: list[object] = []
    with pytest.raises(GitError):
        land(READY, with_step(work_tree(steps), commit_squash=refuse), config=SQUASH)
    assert steps == [("merge", BRANCH), "abort merge"]


def test_a_landing_by_fast_forward_takes_its_git_steps_in_order() -> None:
    steps: list[object] = []
    land(READY, work_tree(steps), config=FAST_FORWARD, message=None)
    assert steps == [
        ("merge", BRANCH),
        "abort merge",
        ("fast-forward", BRANCH),
        RECORD_COMMIT,
        ("remove worktree", WORKTREE),
        ("delete branch", BRANCH),
    ]


def test_a_landing_by_fast_forward_names_the_work_item_and_the_tip_of_the_branch() -> None:
    landed = land(READY, work_tree([]), config=FAST_FORWARD, message=None)
    assert landed == Said("landed S-0001 at 9f8e7d6\n")


def test_a_landing_by_fast_forward_completes_the_work_item_at_the_tip_of_the_branch() -> None:
    saved: list[WorkItemState] = []
    land(READY, work_tree([]), saved, FAST_FORWARD, None)
    assert [item.commit for item in saved if isinstance(item, CompletedWorkItem)] == [
        make_commit("9f8e7d6")
    ]


def test_a_landing_by_fast_forward_with_a_task_not_completed_moves_main_nowhere() -> None:
    steps: list[object] = []
    with pytest.raises(OpenTaskError):
        land(OPEN, work_tree(steps), config=FAST_FORWARD, message=None)
    assert steps == [("merge", BRANCH), "abort merge"]


def test_a_landing_by_fast_forward_is_refused_with_a_message_naming_the_key() -> None:
    with pytest.raises(LandError) as error:
        land(READY, work_tree([]), config=FAST_FORWARD)
    assert str(error.value) == (
        "S-0001 cannot land with --message:"
        " development.merge = fast-forward makes no commit to word"
    )


def test_a_landing_by_fast_forward_refused_with_a_message_takes_no_git_step() -> None:
    steps: list[object] = []
    with pytest.raises(LandError):
        land(READY, work_tree(steps), config=FAST_FORWARD)
    assert steps == []


def test_a_landing_by_fast_forward_is_refused_when_main_holds_a_commit_the_branch_lacks() -> None:
    ahead = with_step(work_tree([]), can_fast_forward=lambda _: False)
    with pytest.raises(LandError) as error:
        land(READY, ahead, config=FAST_FORWARD, message=None)
    assert str(error.value) == (
        f"S-0001 cannot land by fast-forward: main holds a commit {BRANCH} lacks"
        f" -- rebase {BRANCH} on main or merge main into it"
    )


def test_a_landing_by_fast_forward_refused_for_a_commit_of_main_merges_nothing() -> None:
    steps: list[object] = []
    ahead = with_step(work_tree(steps), can_fast_forward=lambda _: False)
    with pytest.raises(LandError):
        land(READY, ahead, config=FAST_FORWARD, message=None)
    assert steps == []


def test_a_fast_forward_git_refuses_takes_no_step_of_the_record() -> None:
    steps: list[object] = []
    with pytest.raises(GitError):
        land(
            READY,
            with_step(work_tree(steps), fast_forward=refuse),
            config=FAST_FORWARD,
            message=None,
        )
    assert steps == [("merge", BRANCH), "abort merge"]


@pytest.mark.parametrize(
    ("config", "message", "moves"),
    [
        (GATED, MESSAGE, [("commit merge", MESSAGE)]),
        (GATED_SQUASH, MESSAGE, [("commit squash", MESSAGE)]),
        (GATED_FAST_FORWARD, None, ["abort merge", ("fast-forward", BRANCH)]),
    ],
    ids=WAYS,
)
def test_a_landing_runs_its_gate_at_the_top_of_the_work_tree_while_the_merge_is_held(
    config: Config, message: str | None, moves: list[object]
) -> None:
    steps: list[object] = []
    land(READY, work_tree(steps), config=config, message=message, run_gate=gate(steps))
    assert steps[:-3] == [("merge", BRANCH), GATE_RUN, *moves]


def test_a_landing_whose_gate_passes_names_the_work_item_and_the_merge_commit() -> None:
    landed = land(READY, work_tree([]), config=GATED, run_gate=gate([]))
    assert landed == Said("landed S-0001 at 3e9ae5c\n")


def test_a_landing_whose_gate_fails_is_refused_naming_the_command_and_its_status() -> None:
    with pytest.raises(GateError) as error:
        land(READY, work_tree([]), config=GATED, run_gate=gate([], 2))
    assert str(error.value) == (
        'S-0001 cannot land: development.gate = "make check" exited with status 2'
    )


@pytest.mark.parametrize(
    ("config", "message"),
    [(GATED, MESSAGE), (GATED_SQUASH, MESSAGE), (GATED_FAST_FORWARD, None)],
    ids=WAYS,
)
def test_a_landing_whose_gate_fails_drops_the_merge_held_and_moves_main_nowhere(
    config: Config, message: str | None
) -> None:
    steps: list[object] = []
    with pytest.raises(GateError):
        land(READY, work_tree(steps), config=config, message=message, run_gate=gate(steps, 1))
    assert steps == [("merge", BRANCH), GATE_RUN, "abort merge"]


@pytest.mark.parametrize(
    ("config", "message"),
    [(GATED, MESSAGE), (GATED_SQUASH, MESSAGE), (GATED_FAST_FORWARD, None)],
    ids=WAYS,
)
def test_a_landing_interrupted_under_its_gate_drops_the_merge_held_and_moves_main_nowhere(
    config: Config, message: str | None
) -> None:
    steps: list[object] = []

    def interrupted(command: str, directory: Path) -> int:
        steps.append(("gate", command, directory))
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        land(READY, work_tree(steps), config=config, message=message, run_gate=interrupted)
    assert steps == [("merge", BRANCH), GATE_RUN, "abort merge"]


def test_a_landing_whose_gate_fails_saves_nothing() -> None:
    saved: list[WorkItemState] = []
    with pytest.raises(GateError):
        land(READY, work_tree([]), saved, GATED, run_gate=gate([], 1))
    assert saved == []


def test_a_landing_with_a_task_not_completed_runs_no_gate() -> None:
    steps: list[object] = []
    with pytest.raises(OpenTaskError):
        land(OPEN, work_tree(steps), config=GATED, run_gate=gate(steps))
    assert steps == [("merge", BRANCH), "abort merge"]
