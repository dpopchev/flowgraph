"""The configuration shown: every key, dotted, with its value as the file writes it."""

import pytest

from flowgraph.config import make_config
from flowgraph.setting import show_config

pytestmark = pytest.mark.view

EVERY_KEY = (
    "[git]\ncommit = true\n"
    '[development]\nenabled = true\nparallel = 2\nmerge = "squash"\ngate = "make check"\n'
)


def test_a_configuration_without_a_key_written_lists_every_key_at_its_default() -> None:
    assert show_config(make_config("")) == (
        "git.commit = true\n"
        "development.enabled = false\n"
        "development.parallel = none\n"
        'development.merge = "merge-commit"\n'
        "development.gate = none\n"
    )


def test_a_configuration_with_every_key_written_lists_each_as_the_file_writes_it() -> None:
    assert show_config(make_config(EVERY_KEY)) == (
        "git.commit = true\n"
        "development.enabled = true\n"
        "development.parallel = 2\n"
        'development.merge = "squash"\n'
        'development.gate = "make check"\n'
    )


def test_a_gate_named_none_is_listed_as_a_text_apart_from_no_gate() -> None:
    shown = show_config(make_config('[development]\ngate = "none"\n'))
    assert shown.splitlines()[-1] == 'development.gate = "none"'


def test_the_commits_turned_off_are_listed_as_false() -> None:
    assert show_config(make_config("[git]\ncommit = false\n")).splitlines()[0] == (
        "git.commit = false"
    )
