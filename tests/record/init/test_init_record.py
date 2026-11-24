"""What fgraph init writes into the record it makes, and the commit it leaves there."""

from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Never

import pytest

from flowgraph.development.commit import Said, WorkTree
from flowgraph.development.git import GitError
from flowgraph.record.config import Settings
from flowgraph.record.init import init_record
from flowgraph.record.location import FindNamed, no_name
from flowgraph.record.store import Store

pytestmark = pytest.mark.command

CWD = Path("/work")
RECORD = CWD / ".fgraph"

# What git refuses in the work tree of a test: its commit, or its check of the ignored paths.
Refusal = Literal["commit", "ignore"] | None


def never_read(*_: object) -> Never:
    """A read of the store, which making a record never asks for."""
    raise AssertionError("making a record reads nothing")


@dataclass
class Effects:
    """What one init did through its injected effects."""

    made: list[Path] = field(default_factory=list[Path])
    saved: list[Settings] = field(default_factory=list[Settings])
    committed: list[tuple[Sequence[Path], str]] = field(
        default_factory=list[tuple[Sequence[Path], str]]
    )
    undone: list[str] = field(default_factory=list[str])


def store(effects: Effects) -> Store:
    """A store whose settings are saved into the effects, and whose changed file is the config."""
    return Store(
        find_work_item_rows=lambda _: [],
        load_work_item=never_read,
        find_work_item_detail=never_read,
        find_task_ids=lambda: [],
        save_work_item=never_read,
        load_queue=never_read,
        save_queue=never_read,
        find_changed_files=lambda: [RECORD / "config.toml"],
        restore_files=lambda: effects.undone.append("restore"),
        save_settings=effects.saved.append,
    )


def work_tree(effects: Effects, refuses: Refusal) -> WorkTree:
    """A git work tree at CWD that records its commits into the effects, and refuses as asked."""

    def commit_files(files: Sequence[Path], message: str) -> str:
        if refuses == "commit":
            raise GitError("git commit failed: refused by the hook")
        effects.committed.append((files, message))
        return "abc1234"

    def ignores(_: Path) -> bool:
        if refuses == "ignore":
            raise GitError("git check-ignore failed: no index")
        return False

    return WorkTree(
        path=CWD,
        commit_files=commit_files,
        add_worktree=never_read,
        current_branch=lambda: "main",
        find_branches=lambda _: [],
        find_worktree=lambda _: None,
        find_worktrees=lambda: [],
        ignores=ignores,
    )


def init(
    effects: Effects,
    *,
    inside_git: bool,
    refuses: Refusal = None,
    given: Path | None = None,
    find_named: FindNamed = no_name,
) -> Said:
    """Init the record of CWD, inside a git work tree or outside any, as git refuses as asked.

    Only CWD and the directory given exist, so a folder named is made in CWD itself.
    """
    return init_record(
        CWD,
        given,
        lambda path: path in (CWD, given),
        effects.made.append,
        lambda path: effects.undone.append(f"remove {path}"),
        lambda _: store(effects),
        lambda _: work_tree(effects, refuses) if inside_git else None,
        find_named,
    )


class TestInitOutsideAGitWorkTree:
    @pytest.fixture
    def effects(self) -> Effects:
        done = Effects()
        init(done, inside_git=False)
        return done

    def test_makes_the_record_directory(self, effects: Effects) -> None:
        assert effects.made == [RECORD]

    def test_saves_a_config_at_the_defaults(self, effects: Effects) -> None:
        assert effects.saved == [{"git": {"commit": True}, "development": {"enabled": False}}]

    def test_commits_nothing(self, effects: Effects) -> None:
        assert effects.committed == []

    def test_removes_nothing(self, effects: Effects) -> None:
        assert effects.undone == []


class TestInitInsideAGitWorkTree:
    @pytest.fixture
    def effects(self) -> Effects:
        done = Effects()
        init(done, inside_git=True)
        return done

    def test_commits_the_config_alone(self, effects: Effects) -> None:
        assert [files for files, _ in effects.committed] == [[Path(".fgraph/config.toml")]]

    def test_commits_it_as_a_write_of_the_record(self, effects: Effects) -> None:
        assert [message for _, message in effects.committed] == ["chore: make the record"]

    def test_removes_nothing(self, effects: Effects) -> None:
        assert effects.undone == []


class TestInitWhoseCommitGitRefuses:
    @pytest.fixture
    def effects(self) -> Effects:
        done = Effects()
        with suppress(GitError):
            init(done, inside_git=True, refuses="commit")
        return done

    def test_removes_the_directory_last(self, effects: Effects) -> None:
        assert effects.undone[-1:] == ["remove /work/.fgraph"]


class TestInitWhoseIgnoreGitRefuses:
    @pytest.fixture
    def effects(self) -> Effects:
        done = Effects()
        with suppress(GitError):
            init(done, inside_git=True, refuses="ignore")
        return done

    def test_restores_the_file_then_removes_the_directory(self, effects: Effects) -> None:
        assert effects.undone == ["restore", "remove /work/.fgraph"]


def test_passes_the_refusal_of_git_on_as_it_was() -> None:
    with pytest.raises(GitError, match=r"^git commit failed: refused by the hook$"):
        init(Effects(), inside_git=True, refuses="commit")


def test_says_the_record_it_made() -> None:
    assert init(Effects(), inside_git=False).out == "record: /work/.fgraph\n"


NAMED = CWD / ".dpopchev"


def test_makes_the_folder_the_key_names() -> None:
    effects = Effects()
    init(effects, inside_git=False, find_named=lambda _: NAMED)
    assert effects.made == [NAMED]


def test_says_the_folder_the_key_names() -> None:
    said = init(Effects(), inside_git=False, find_named=lambda _: NAMED)
    assert said.out == "record: /work/.dpopchev\n"


def test_asks_the_key_for_the_directory_it_runs_in() -> None:
    asked: list[Path] = []

    def find_named(directory: Path) -> None:
        asked.append(directory)

    init(Effects(), inside_git=False, find_named=find_named)
    assert asked == [CWD]


def never_named(directory: Path) -> Path | None:
    """A find_named that fails the test when it is asked."""
    raise AssertionError(f"find_named asked for {directory}")


def test_makes_the_record_in_the_directory_given_without_asking_the_key() -> None:
    effects = Effects()
    given = CWD / "other"
    init(effects, inside_git=False, given=given, find_named=never_named)
    assert effects.made == [given / ".fgraph"]
