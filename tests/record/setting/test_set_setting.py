"""The set command: it loads the settings whole, sets one key, saves them whole."""

import pytest

from flowgraph.item.commands import Written
from flowgraph.record import ConfigError, Settings, make_config
from flowgraph.record.setting import set_setting

pytestmark = pytest.mark.command

ENABLED = {"development": {"enabled": True}}
BOTH = {"development": {"enabled": True, "parallel": 2}}


def test_a_set_saves_the_settings_with_the_key_set() -> None:
    saved: list[Settings] = []
    set_setting("development.parallel", "2", lambda: ENABLED, saved.append)
    assert saved == [BOTH]


def test_a_set_says_the_key_with_its_value_under_the_message_of_its_commit() -> None:
    done = set_setting("development.parallel", "2", lambda: ENABLED, lambda _: None)
    assert done.written == Written(
        "set development.parallel = 2\n", "chore: set development.parallel in the record"
    )


def test_a_set_says_a_text_as_the_file_writes_it() -> None:
    done = set_setting("development.gate", "make check", lambda: ENABLED, lambda _: None)
    assert done.written.out == 'set development.gate = "make check"\n'


def test_a_set_holds_the_configuration_it_leaves() -> None:
    done = set_setting("git.commit", "false", dict, lambda _: None)
    assert done.config == make_config("[git]\ncommit = false\n")


def test_a_set_refused_saves_nothing() -> None:
    saved: list[Settings] = []
    with pytest.raises(ConfigError):
        set_setting("development.parallel", "0", lambda: ENABLED, saved.append)
    assert saved == []
