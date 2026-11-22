"""What fgraph init writes into the record it makes, and the commit it leaves there."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Never

import pytest

from flowgraph.development.commit import Said, WorkTree
from flowgraph.record.config import Settings
from flowgraph.record.init import init_record
from flowgraph.record.store import Store

pytestmark = pytest.mark.command

CWD = Path("/work")
RECORD = CWD / ".fgraph"


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
        restore_files=lambda: None,
        save_settings=effects.saved.append,
    )


def work_tree(effects: Effects) -> WorkTree:
    """A git work tree at CWD that records its commits into the effects."""

    def commit_files(files: Sequence[Path], message: str) -> str:
        effects.committed.append((files, message))
        return "abc1234"

    return WorkTree(
        path=CWD,
        commit_files=commit_files,
        add_worktree=never_read,
        current_branch=lambda: "main",
        find_branches=lambda _: [],
        find_worktree=lambda _: None,
        find_worktrees=lambda: [],
    )


def init(effects: Effects, *, inside_git: bool) -> Said:
    """Init the record of CWD, inside a git work tree or outside any."""
    return init_record(
        CWD,
        None,
        lambda _: False,
        effects.made.append,
        lambda _: store(effects),
        lambda _: work_tree(effects) if inside_git else None,
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


def test_says_the_record_it_made() -> None:
    assert init(Effects(), inside_git=False).out == "record: /work/.fgraph\n"
