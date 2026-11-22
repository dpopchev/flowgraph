"""The settings of a record: the keys its `config.toml` writes, read and written as that file."""

from pathlib import Path

import pytest

from flowgraph.record.config import ConfigError, read_settings, write_settings

pytestmark = pytest.mark.edge

FILE = "config.toml"
ENABLED = "[development]\nenabled = true\n"
WRITTEN = {
    "git": {"commit": True},
    "development": {"enabled": True, "parallel": 2, "merge": "squash", "gate": "make check"},
}
REFUSED = {"git": {"commit": False}, "development": {"enabled": True}}


def test_a_record_without_a_config_file_writes_no_setting(tmp_path: Path) -> None:
    assert read_settings(tmp_path) == {}


def test_the_settings_of_a_record_are_the_keys_its_file_writes(tmp_path: Path) -> None:
    (tmp_path / FILE).write_text(ENABLED, encoding="utf-8")
    assert read_settings(tmp_path) == {"development": {"enabled": True}}


def test_the_settings_of_a_file_refused_name_its_path_and_the_key(tmp_path: Path) -> None:
    (tmp_path / FILE).write_text("[development]\nenable = true\n", encoding="utf-8")
    with pytest.raises(ConfigError) as error:
        read_settings(tmp_path)
    assert str(error.value) == (
        f"{tmp_path / FILE}: development.enable is no key of the configuration"
    )


def test_settings_are_written_as_a_table_per_layer(tmp_path: Path) -> None:
    write_settings(tmp_path, {"development": {"enabled": True}})
    assert (tmp_path / FILE).read_text(encoding="utf-8") == ENABLED


def test_settings_read_back_whole(tmp_path: Path) -> None:
    write_settings(tmp_path, WRITTEN)
    assert read_settings(tmp_path) == WRITTEN


@pytest.mark.parametrize(
    ("settings", "why"),
    [
        (
            {"development": {"enable": True}},
            "development.enable is no key of the configuration",
        ),
        (
            {"development": {"parallel": 0}},
            "development.parallel is 0: it takes a whole number of 1 or more",
        ),
        (
            REFUSED,
            "development.enabled is true while git.commit is false:"
            " the development needs the commits of the record",
        ),
    ],
    ids=["no-key", "no-value-of-the-key", "development-on-with-the-commits-off"],
)
def test_settings_that_hold_no_configuration_are_refused_naming_the_key(
    tmp_path: Path, settings: dict[str, dict[str, object]], why: str
) -> None:
    with pytest.raises(ConfigError) as error:
        write_settings(tmp_path, settings)
    assert str(error.value) == why


class TestAWriteRefused:
    @pytest.fixture
    def record(self, tmp_path: Path) -> Path:
        """A record whose config.toml turns the development on, after a write that is refused."""
        (tmp_path / FILE).write_text(ENABLED, encoding="utf-8")
        with pytest.raises(ConfigError):
            write_settings(tmp_path, REFUSED)
        return tmp_path

    def test_keeps_the_previous_content(self, record: Path) -> None:
        assert (record / FILE).read_text(encoding="utf-8") == ENABLED

    def test_leaves_no_other_file_in_the_record(self, record: Path) -> None:
        assert [path.name for path in record.iterdir()] == [FILE]


def test_a_write_refused_on_a_record_without_a_config_file_makes_none(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        write_settings(tmp_path, REFUSED)
    assert list(tmp_path.iterdir()) == []
