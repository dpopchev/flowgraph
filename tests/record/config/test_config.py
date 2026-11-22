"""The configuration of a record: `config.toml` in the record, a table per layer it turns on."""

from pathlib import Path

import pytest

from flowgraph.record.config import ConfigError, make_config, read_config
from flowgraph.record.layers import UNGATED, UNLIMITED, Gated, Merge, Parallel

pytestmark = pytest.mark.edge

FILE = "config.toml"
ENABLED = "[development]\nenabled = true\n"
UNCOMMITTED = "[git]\ncommit = false\n"
TAKES_A_COUNT = "it takes a whole number of 1 or more"
TAKES_A_WAY = "it takes merge-commit, squash or fast-forward"
TAKES_A_COMMAND = "it takes a command line"


@pytest.mark.parametrize(
    ("text", "enabled"),
    [("", False), ("[development]\n", False), ("[development]\nenabled = false\n", False)],
    ids=["no-table", "no-key", "written-off"],
)
def test_the_development_is_off_unless_enabled(text: str, enabled: bool) -> None:
    assert make_config(text).development.enabled is enabled


def test_the_development_enabled_is_on() -> None:
    assert make_config(ENABLED).development.enabled is True


@pytest.mark.parametrize(
    "text",
    ["", "[development]\n", ENABLED],
    ids=["no-table", "no-key", "development-on"],
)
def test_the_work_items_started_at_once_are_unlimited_unless_parallel_is_set(text: str) -> None:
    assert make_config(text).development.parallel == UNLIMITED


@pytest.mark.parametrize(
    ("text", "most"),
    [(f"{ENABLED}parallel = 1\n", 1), (f"{ENABLED}parallel = 3\n", 3)],
    ids=["one", "several"],
)
def test_parallel_set_is_the_most_work_items_started_at_once(text: str, most: int) -> None:
    assert make_config(text).development.parallel == Parallel(most)


def test_parallel_is_held_as_written_with_the_development_off() -> None:
    assert make_config("[development]\nparallel = 2\n").development.parallel == Parallel(2)


@pytest.mark.parametrize(
    ("value", "written"),
    [("0", "0"), ("-1", "-1"), ("1.5", "1.5"), ('"2"', '"2"'), ("true", "true")],
    ids=["zero", "negative", "fraction", "text", "true"],
)
def test_a_parallel_that_is_no_whole_number_of_one_or_more_is_refused_naming_the_key(
    value: str, written: str
) -> None:
    with pytest.raises(ConfigError) as error:
        make_config(f"[development]\nparallel = {value}\n")
    assert str(error.value) == f"development.parallel is {written}: {TAKES_A_COUNT}"


@pytest.mark.parametrize(
    "text",
    ["", "[development]\n", ENABLED],
    ids=["no-table", "no-key", "development-on"],
)
def test_a_landing_merges_by_a_merge_commit_unless_merge_is_set(text: str) -> None:
    assert make_config(text).development.merge is Merge.MERGE_COMMIT


@pytest.mark.parametrize(
    ("word", "merge"),
    [
        ("merge-commit", Merge.MERGE_COMMIT),
        ("squash", Merge.SQUASH),
        ("fast-forward", Merge.FAST_FORWARD),
    ],
)
def test_merge_set_is_how_a_landing_merges(word: str, merge: Merge) -> None:
    assert make_config(f'{ENABLED}merge = "{word}"\n').development.merge is merge


def test_merge_is_held_as_written_with_the_development_off() -> None:
    assert make_config('[development]\nmerge = "squash"\n').development.merge is Merge.SQUASH


@pytest.mark.parametrize(
    "value",
    ['"rebase"', '"Squash"', '""', "1", "true"],
    ids=["another-word", "another-case", "no-word", "number", "true"],
)
def test_a_merge_that_is_no_way_of_merging_is_refused_naming_the_key(value: str) -> None:
    with pytest.raises(ConfigError) as error:
        make_config(f"[development]\nmerge = {value}\n")
    assert str(error.value) == f"development.merge is {value}: {TAKES_A_WAY}"


@pytest.mark.parametrize(
    "text",
    ["", "[development]\n", ENABLED],
    ids=["no-table", "no-key", "development-on"],
)
def test_a_landing_is_ungated_unless_gate_is_set(text: str) -> None:
    assert make_config(text).development.gate == UNGATED


def test_gate_set_is_the_command_line_a_landing_runs() -> None:
    assert make_config(f'{ENABLED}gate = "make check"\n').development.gate == Gated("make check")


def test_gate_is_held_as_written_with_the_development_off() -> None:
    assert make_config('[development]\ngate = "make check"\n').development.gate == Gated(
        "make check"
    )


@pytest.mark.parametrize(
    "text",
    ["", "[delivery]\n", "[delivery]\npush = false\n", ENABLED],
    ids=["no-table", "no-key", "written-off", "development-on"],
)
def test_a_landing_pushes_nothing_unless_delivery_push_is_set(text: str) -> None:
    assert make_config(text).delivery.push is False


def test_delivery_push_set_pushes_a_landing() -> None:
    assert make_config(f"{ENABLED}[delivery]\npush = true\n").delivery.push is True


def test_delivery_push_is_held_as_written_with_the_development_off() -> None:
    assert make_config("[delivery]\npush = true\n").delivery.push is True


@pytest.mark.parametrize(
    "value",
    ['""', '"  "', "1", "true", '["make", "check"]'],
    ids=["empty", "blank", "number", "true", "words"],
)
def test_a_gate_that_is_no_command_line_is_refused_naming_the_key(value: str) -> None:
    with pytest.raises(ConfigError) as error:
        make_config(f"[development]\ngate = {value}\n")
    assert str(error.value) == f"development.gate is {value}: {TAKES_A_COMMAND}"


@pytest.mark.parametrize(
    "text",
    ["", "[git]\n", "[git]\ncommit = true\n", ENABLED, f"{ENABLED}[git]\ncommit = true\n"],
    ids=["no-table", "no-key", "written-on", "development-on", "both-on"],
)
def test_the_commits_are_on_unless_turned_off(text: str) -> None:
    assert make_config(text).git.commit is True


def test_the_commits_turned_off_are_off() -> None:
    assert make_config(UNCOMMITTED).git.commit is False


@pytest.mark.parametrize(
    "text",
    [f"{ENABLED}{UNCOMMITTED}", f"{UNCOMMITTED}{ENABLED}"],
    ids=["development-first", "git-first"],
)
def test_the_development_enabled_with_the_commits_off_is_refused_naming_both_keys(
    text: str,
) -> None:
    with pytest.raises(ConfigError) as error:
        make_config(text)
    assert str(error.value) == (
        "development.enabled is true while git.commit is false:"
        " the development needs the commits of the record"
    )


@pytest.mark.parametrize(
    ("text", "why"),
    [
        ("[tools]\n", "tools is no table of the configuration"),
        ("enabled = true\n", "enabled is no table of the configuration"),
        (
            "[development]\nenable = true\n",
            "development.enable is no key of the configuration",
        ),
        (
            '[development]\nenabled = "yes"\n',
            'development.enabled is "yes": it takes true or false',
        ),
        ("[development]\nenabled = 1\n", "development.enabled is 1: it takes true or false"),
        ("development = true\n", "development is true: it takes a table"),
        ("[git]\ncommits = false\n", "git.commits is no key of the configuration"),
        ('[git]\ncommit = "no"\n', 'git.commit is "no": it takes true or false'),
        ("git = false\n", "git is false: it takes a table"),
        ("[delivery]\npushes = true\n", "delivery.pushes is no key of the configuration"),
        ('[delivery]\npush = "yes"\n', 'delivery.push is "yes": it takes true or false'),
        ("delivery = true\n", "delivery is true: it takes a table"),
    ],
    ids=[
        "table",
        "key-of-no-table",
        "key",
        "text-value",
        "number-value",
        "value-for-a-table",
        "key-of-git",
        "text-value-of-git",
        "value-for-git",
        "key-of-delivery",
        "text-value-of-delivery",
        "value-for-delivery",
    ],
)
def test_a_text_refused_names_the_key(text: str, why: str) -> None:
    with pytest.raises(ConfigError) as error:
        make_config(text)
    assert str(error.value) == why


def test_a_text_that_is_no_toml_is_refused() -> None:
    with pytest.raises(ConfigError, match=r"^no TOML: "):
        make_config("[development\n")


def test_a_record_without_a_config_file_holds_the_defaults(tmp_path: Path) -> None:
    assert read_config(tmp_path) == make_config("")


def test_the_config_file_of_a_record_is_read(tmp_path: Path) -> None:
    (tmp_path / FILE).write_text(ENABLED, encoding="utf-8")
    assert read_config(tmp_path) == make_config(ENABLED)


def test_a_file_refused_names_its_path_and_the_key(tmp_path: Path) -> None:
    (tmp_path / FILE).write_text("[development]\nenable = true\n", encoding="utf-8")
    with pytest.raises(ConfigError) as error:
        read_config(tmp_path)
    assert str(error.value) == (
        f"{tmp_path / FILE}: development.enable is no key of the configuration"
    )
