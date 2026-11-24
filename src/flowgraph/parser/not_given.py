"""The callable run() of src/flowgraph/cli.py takes for an effect when it is given none.

A wait that does not wait, the configuration at its defaults, and for the rest a contract that
raises, since such a run must not make that effect.
"""

from pathlib import Path
from typing import Never

from flowgraph.record import Config, make_config


def no_wait(seconds: float) -> None:
    """The wait of a run given none: the next frame of watch follows at once."""


def no_config(record: Path) -> Config:
    """The configuration of a run given none to read: the defaults, whatever the record holds."""
    return make_config("")


def no_gate(command: str, directory: Path) -> Never:
    """The gate of a run given none to run it: a contract, such a run lands under no gate."""
    raise AssertionError(f"run() was given no run_gate to run {command!r} in {directory}")


def no_check(command: str, directory: Path) -> Never:
    """The check runner of a run given none: a contract, such a run completes no checked Task."""
    raise AssertionError(f"run() was given no run_check to run {command!r} in {directory}")


def no_dir(path: Path) -> Never:
    """The make_dir of a run given none: a contract, such a run makes no record."""
    raise AssertionError(f"run() was given no make_dir to make {path}")


def no_removal(path: Path) -> Never:
    """The remove_dir of a run given none: a contract, such a run removes no record."""
    raise AssertionError(f"run() was given no remove_dir to remove {path}")
