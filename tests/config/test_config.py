"""The configuration of a record: `config.toml` in the record, a table per layer it turns on."""

from pathlib import Path

import pytest

from flowgraph.config import ConfigError, make_config, read_config

pytestmark = pytest.mark.edge

FILE = "config.toml"
ENABLED = "[development]\nenabled = true\n"


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
    ],
    ids=["table", "key-of-no-table", "key", "text-value", "number-value", "value-for-a-table"],
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
