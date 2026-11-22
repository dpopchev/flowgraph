"""The check of a Task at its complete: the runner is given the command and the directory."""

from pathlib import Path

import pytest

from flowgraph.development.task_check import TaskCheckError, check_task_passes

pytestmark = pytest.mark.model

WHERE = Path("/src/project.worktrees/S-0001-a-story")


def test_the_runner_is_given_the_command_and_the_directory() -> None:
    asked: list[tuple[str, Path]] = []

    def run(command: str, directory: Path) -> int:
        asked.append((command, directory))
        return 0

    check_task_passes("T-0001", "make test", WHERE, run)
    assert asked == [("make test", WHERE)]


def test_a_check_that_exits_with_zero_is_taken() -> None:
    assert check_task_passes("T-0001", "make test", WHERE, lambda command, directory: 0) is None


def test_a_check_that_exits_with_another_status_is_refused_naming_the_task_and_the_status() -> None:
    with pytest.raises(
        TaskCheckError,
        match=r'^T-0001 cannot complete: its check "make test" exited with status 2$',
    ):
        check_task_passes("T-0001", "make test", WHERE, lambda command, directory: 2)


@pytest.mark.parametrize("check", [None, ""])
def test_a_task_that_holds_no_check_never_calls_the_runner(check: str | None) -> None:
    def run(command: str, directory: Path) -> int:
        raise AssertionError("the runner was called")

    assert check_task_passes("T-0001", check, WHERE, run) is None
