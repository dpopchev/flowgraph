"""One key set among the settings: its value read by what the key takes, the others kept."""

import pytest

from flowgraph.record import ConfigError
from flowgraph.record.setting import with_setting

pytestmark = pytest.mark.model

ENABLED = {"development": {"enabled": True}}
TAKES_A_COUNT = "it takes a whole number of 1 or more"
TAKES_A_TAG = "it takes feature-close, close or none"


@pytest.mark.parametrize(
    ("key", "text", "settings"),
    [
        ("git.commit", "false", {"git": {"commit": False}}),
        ("git.commit", "true", {"git": {"commit": True}}),
        ("development.enabled", "true", {"development": {"enabled": True}}),
        ("development.parallel", "2", {"development": {"parallel": 2}}),
        ("development.merge", "squash", {"development": {"merge": "squash"}}),
        ("development.gate", "make check", {"development": {"gate": "make check"}}),
        ("development.gate", "true", {"development": {"gate": "true"}}),
        ("development.gate", "1", {"development": {"gate": "1"}}),
        ("development.driver", "agent", {"development": {"driver": "agent"}}),
        ("development.driver", "developer", {"development": {"driver": "developer"}}),
        ("development.mode", "trunk", {"development": {"mode": "trunk"}}),
        ("development.branch_max", "2d", {"development": {"branch_max": "2d"}}),
        ("delivery.push", "true", {"delivery": {"push": True}}),
        ("delivery.tag", "feature-close", {"delivery": {"tag": "feature-close"}}),
        ("delivery.tag", "close", {"delivery": {"tag": "close"}}),
        ("delivery.tag", "none", {"delivery": {"tag": "none"}}),
        ("archive.board", ".board", {"archive": {"board": ".board"}}),
    ],
    ids=[
        "false",
        "true",
        "enabled",
        "a-count",
        "a-way-of-merging",
        "a-command-line",
        "a-command-named-true",
        "a-command-named-one",
        "an-agent",
        "a-developer",
        "the-trunk",
        "an-age",
        "a-push",
        "a-tag-at-the-close-of-a-feature",
        "a-tag-at-the-close-of-a-work-item",
        "no-tag",
        "a-path",
    ],
)
def test_the_text_of_a_value_is_read_as_the_value_its_key_takes(
    key: str, text: str, settings: dict[str, dict[str, object]]
) -> None:
    assert with_setting({}, key, text) == settings


def test_a_key_set_keeps_the_other_keys_of_its_table() -> None:
    assert with_setting(ENABLED, "development.parallel", "2") == {
        "development": {"enabled": True, "parallel": 2}
    }


def test_a_key_set_keeps_the_other_tables() -> None:
    assert with_setting(ENABLED, "git.commit", "true") == {
        "development": {"enabled": True},
        "git": {"commit": True},
    }


def test_a_key_set_again_holds_the_value_set_last() -> None:
    assert with_setting(ENABLED, "development.enabled", "false") == {
        "development": {"enabled": False}
    }


def test_a_key_set_leaves_the_settings_given_as_they_were() -> None:
    settings = {"development": {"enabled": True}}
    with_setting(settings, "development.parallel", "2")
    assert settings == ENABLED


@pytest.mark.parametrize(
    "key",
    ["development.enable", "development", "enabled", "tools.gate", "", "git.commit.now"],
    ids=["no-key-of-its-table", "a-table", "no-table", "no-such-table", "blank", "deeper"],
)
def test_a_key_the_configuration_does_not_have_is_refused_naming_it(key: str) -> None:
    with pytest.raises(ConfigError) as error:
        with_setting({}, key, "true")
    assert str(error.value) == f"{key} is no key of the configuration"


@pytest.mark.parametrize(
    ("key", "text", "why"),
    [
        ("git.commit", "no", 'git.commit is "no": it takes true or false'),
        ("development.enabled", "1", 'development.enabled is "1": it takes true or false'),
        ("development.enabled", "True", 'development.enabled is "True": it takes true or false'),
        ("development.parallel", "0", f"development.parallel is 0: {TAKES_A_COUNT}"),
        ("development.parallel", "-1", f"development.parallel is -1: {TAKES_A_COUNT}"),
        ("development.parallel", "1.5", f'development.parallel is "1.5": {TAKES_A_COUNT}'),
        ("development.parallel", "two", f'development.parallel is "two": {TAKES_A_COUNT}'),
        ("development.parallel", "true", f'development.parallel is "true": {TAKES_A_COUNT}'),
        (
            "development.merge",
            "rebase",
            'development.merge is "rebase":'
            " it takes merge-commit, squash, fast-forward or pull-request",
        ),
        ("development.gate", "", 'development.gate is "": it takes a command line'),
        ("development.gate", "  ", 'development.gate is "  ": it takes a command line'),
        (
            "development.driver",
            "robot",
            'development.driver is "robot": it takes developer or agent',
        ),
        ("development.mode", "main", 'development.mode is "main": it takes branch or trunk'),
        (
            "development.branch_max",
            "soon",
            'development.branch_max is "soon": it takes a whole number of days of 1 or more, as 1d',
        ),
        ("delivery.push", "yes", 'delivery.push is "yes": it takes true or false'),
        ("delivery.tag", "sometimes", f'delivery.tag is "sometimes": {TAKES_A_TAG}'),
        ("delivery.tag", "true", f'delivery.tag is "true": {TAKES_A_TAG}'),
        ("archive.board", "", 'archive.board is "": it takes a path'),
        ("archive.board", "  ", 'archive.board is "  ": it takes a path'),
    ],
    ids=[
        "another-word-for-false",
        "a-number-for-true",
        "another-case",
        "zero",
        "negative",
        "fraction",
        "a-word-for-a-count",
        "true-for-a-count",
        "no-way-of-merging",
        "an-empty-gate",
        "a-blank-gate",
        "no-driver",
        "no-mode",
        "no-age",
        "another-word-for-a-push",
        "no-word-of-a-tag",
        "a-truth-for-a-tag",
        "an-empty-path",
        "a-blank-path",
    ],
)
def test_a_value_its_key_does_not_take_is_refused_naming_the_key(
    key: str, text: str, why: str
) -> None:
    with pytest.raises(ConfigError) as error:
        with_setting({}, key, text)
    assert str(error.value) == why


@pytest.mark.parametrize(
    ("settings", "key", "text"),
    [
        ({"git": {"commit": False}}, "development.enabled", "true"),
        ({"development": {"enabled": True}}, "git.commit", "false"),
    ],
    ids=["development-on-with-the-commits-off", "commits-off-with-the-development-on"],
)
def test_a_key_set_that_turns_the_development_on_with_the_commits_off_is_refused(
    settings: dict[str, dict[str, object]], key: str, text: str
) -> None:
    with pytest.raises(ConfigError) as error:
        with_setting(settings, key, text)
    assert str(error.value) == (
        "development.enabled is true while git.commit is false:"
        " the development needs the commits of the record"
    )
