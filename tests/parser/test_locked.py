"""The commands that take the lock of their record: every one but those that write nothing."""

import argparse

import pytest

from flowgraph.parser.locked import READS, takes_lock

pytestmark = pytest.mark.view

WRITES = (
    *("add", "amend", "start", "block", "unblock", "complete", "land", "remove", "note"),
    *("verify", "release", "relate", "reorder", "hand", "sync"),
)


@pytest.mark.parametrize("command", READS)
def test_a_command_that_writes_nothing_takes_no_lock(command: str) -> None:
    assert takes_lock(argparse.Namespace(command=command)) is False


def test_config_show_takes_no_lock() -> None:
    assert takes_lock(argparse.Namespace(command="config", action="show")) is False


def test_no_command_takes_no_lock() -> None:
    assert takes_lock(argparse.Namespace(command=None)) is False


@pytest.mark.parametrize("command", WRITES)
def test_a_command_that_writes_takes_the_lock(command: str) -> None:
    assert takes_lock(argparse.Namespace(command=command)) is True


@pytest.mark.parametrize("action", ["set", "unset"])
def test_config_that_sets_a_key_takes_the_lock(action: str) -> None:
    assert takes_lock(argparse.Namespace(command="config", action=action)) is True
