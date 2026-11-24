"""The check of the files a completion's commit changed: each must be named by the brief.

The fake work tree answers what git answers for a sha: the files it changed. The check asks
git for nothing before the development is on, a sha is given and a started Task is found.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Never

import pytest

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.development.commit import WorkTree
from flowgraph.development.named_files import FilesNotNamedError, check_files_named
from flowgraph.record import Config, make_config
from flowgraph.record.queue import make_queue
from flowgraph.record.store import Store
from flowgraph.story import STORY, make_story_id
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    WorkItemState,
    append_task,
    blocked_work_item,
    completed_task,
    make_work_item,
    started_task,
    started_work_item,
    work_item_row,
)

pytestmark = pytest.mark.command

HERE = Path("/src/project")
RECORD = HERE / ".fgraph"
SHA = "3e9ae5c"
CREATED = datetime(2026, 1, 1, tzinfo=UTC)
ON = make_config("[development]\nenabled = true\n")
OFF = make_config("")


def task_texts(title: str, output: str, description: str) -> WorkItemState:
    """A started Story whose one Task, T-0001, is started and holds those three texts."""
    task = make_task(make_task_id(1), title, output, description, CREATED, "make test")
    story = make_work_item(make_story_id(1), "a title", make_scenario("a", "b", "c"), "", CREATED)
    started = started_work_item(append_task(story, task), CREATED)
    return started_task(started, make_task_id(1), CREATED)


STARTED = task_texts("Change src/a.py", "an output", "")


def never(*_: object) -> Never:
    """A read or a step that the check asks for in no case in which the test uses it."""
    raise AssertionError("the check asks nothing here")


def unread() -> Store:
    """A store the check never reads."""
    return Store(
        find_work_item_rows=never,
        load_work_item=never,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=never,
        load_queue=never,
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
    )


def holding(item: WorkItemState) -> Store:
    """The store of a record holding that Story alone."""
    return Store(
        find_work_item_rows=lambda kind: [work_item_row(item)] if kind == STORY else [],
        load_work_item=lambda _: item,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=never,
        load_queue=lambda: make_queue([]),
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
    )


def work_tree(answer: list[str] | None, asked: list[str] | None = None) -> WorkTree:
    """A work tree at HERE whose changed_files answers that, recording each sha it is asked."""

    def changed_files(sha: str) -> list[str] | None:
        if asked is not None:
            asked.append(sha)
        return answer

    return WorkTree(
        path=HERE,
        commit_files=never,
        add_worktree=never,
        current_branch=never,
        find_branches=never,
        find_worktree=never,
        find_worktrees=never,
        changed_files=changed_files,
    )


def check(changed: list[str] | None, item: WorkItemState = STARTED, record: Path = RECORD) -> None:
    """Check T-0001 at the commit, which changed those files, with the development on."""
    check_files_named("T-0001", SHA, holding(item), record, lambda _: work_tree(changed), ON)


def test_a_commit_of_a_file_the_brief_names_passes() -> None:
    assert check(["src/a.py"]) is None


def test_a_commit_that_changed_a_file_the_brief_does_not_name_is_refused_naming_it() -> None:
    with pytest.raises(
        FilesNotNamedError,
        match=r"^T-0001 cannot complete: the commit 3e9ae5c changed what its brief does not name:"
        r" other.txt$",
    ):
        check(["src/a.py", "other.txt"])


def test_every_file_the_brief_does_not_name_is_listed() -> None:
    with pytest.raises(FilesNotNamedError, match=r": docs/m.md, other.txt$"):
        check(["docs/m.md", "other.txt"])


def test_a_file_of_the_record_is_never_asked() -> None:
    assert check([".fgraph/stories/S-0001.toml"]) is None


def test_a_file_of_a_record_below_the_top_is_never_asked() -> None:
    assert check(["sub/.fgraph/x.toml"], record=HERE / "sub" / ".fgraph") is None


def test_a_file_of_the_top_named_fgraph_is_asked_when_the_record_is_below_the_top() -> None:
    with pytest.raises(FilesNotNamedError, match=r": .fgraph/x.toml$"):
        check([".fgraph/x.toml"], record=HERE / "sub" / ".fgraph")


@pytest.mark.parametrize(
    "item",
    [
        task_texts("a title", "changed: src/a.py", ""),
        task_texts("a title", "an output", "src/a.py"),
    ],
    ids=["output", "description"],
)
def test_a_file_named_by_one_text_of_the_brief_passes(item: WorkItemState) -> None:
    assert check(["src/a.py"], item) is None


def test_a_commit_that_changed_no_file_passes() -> None:
    assert check([]) is None


def test_a_commit_git_does_not_know_passes() -> None:
    assert check(None) is None


def test_the_sha_git_is_asked_is_the_one_given() -> None:
    asked: list[str] = []
    check_files_named("T-0001", SHA, holding(STARTED), RECORD, lambda _: work_tree([], asked), ON)
    assert asked == [SHA]


@pytest.mark.parametrize(
    ("item", "sha", "config"),
    [
        ("T-0001", SHA, OFF),
        ("T-0001", None, ON),
        ("S-0001", SHA, ON),
        ("F-0001", SHA, ON),
        ("no id", SHA, ON),
        ("T-0001", "xyz", ON),
    ],
    ids=["development-off", "no-sha", "work-item", "feature", "no-id", "no-sha-text"],
)
def test_nothing_is_read_when_nothing_is_checked(
    item: str, sha: str | None, config: Config
) -> None:
    assert check_files_named(item, sha, unread(), RECORD, never, config) is None


def test_a_work_tree_git_does_not_give_passes() -> None:
    assert check_files_named("T-0001", SHA, holding(STARTED), RECORD, lambda _: None, ON) is None


@pytest.mark.parametrize(
    "item",
    [
        make_work_item(make_story_id(1), "a title", make_scenario("a", "b", "c"), "", CREATED),
        started_work_item(
            append_task(
                make_work_item(
                    make_story_id(1), "a title", make_scenario("a", "b", "c"), "", CREATED
                ),
                make_task(make_task_id(1), "Change src/a.py", "an output", "", CREATED, "true"),
            ),
            CREATED,
        ),
        completed_task(STARTED, make_task_id(1), CREATED, make_commit("abc1234")),
        blocked_work_item(STARTED, "no key", "developer", CREATED),
    ],
    ids=["no-task", "in-backlog", "completed", "blocked-work-item"],
)
def test_a_task_that_is_not_started_asks_git_nothing(item: WorkItemState) -> None:
    assert check_files_named("T-0001", SHA, holding(item), RECORD, never, ON) is None
