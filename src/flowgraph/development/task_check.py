"""The check of a Task: its command is needed with the development on, refused with it off.

A Task that holds one is completed only while it passes: the complete runs it through a runner
given as a callable, the kind the gate of a landing is run through.
"""

from pathlib import Path

from flowgraph.development.gate import RunGate
from flowgraph.record import DEVELOPMENT_ENABLED


class CheckError(ValueError):
    """A Task added without its check while the development is on, or with one while it is off."""


class TaskCheckError(Exception):
    """A Task completed while its check fails; names the Task, the command and its status."""


def check_task_passes(task: str, check: str | None, directory: Path, run_check: RunGate) -> None:
    """Run the check of the Task in the directory; a Task that holds none runs nothing.

    Raises TaskCheckError naming the Task, the command and its status when it exits with another
    status than 0.
    """
    if not check:
        return
    status = run_check(check, directory)
    if status != 0:
        said = f'its check "{check}" exited with status {status}'
        raise TaskCheckError(f"{task} cannot complete: {said}")


def check_task_checked(check: str | None, development_on: bool, config_file: Path) -> None:
    """Refuse a Task added without a check with the development on, or with one with it off.

    Raises CheckError naming --check when it is left out with the development on, and naming the
    key that turns the development on, in that file, when one is given with it off.
    """
    if development_on and check is None:
        raise CheckError("the development is on, so a Task is added with --check COMMAND")
    if check is not None and not development_on:
        turn_on = f"set {DEVELOPMENT_ENABLED} = true in {config_file}"
        raise CheckError(f"a Task takes no --check: the development is off -- {turn_on}")
