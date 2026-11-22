"""The settings of a store: read and written as the config.toml of its record, journaled."""

from pathlib import Path
from typing import Never

import pytest

from flowgraph.record import ConfigError
from flowgraph.record.store import NoSettingsStoreError, Store, open_files

pytestmark = pytest.mark.edge

FILE = "config.toml"
ENABLED = "[development]\nenabled = true\n"
SETTINGS = {"development": {"enabled": True}}
LIMITED = {"development": {"enabled": True, "parallel": 2}}


def never(*_: object) -> Never:
    """A read or a write of the record that the settings of a store never ask for."""
    raise AssertionError("the settings of a store ask for no other read or write")


def without_settings() -> Store:
    """A store built without the settings of its record."""
    return Store(
        find_work_item_rows=never,
        load_work_item=never,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=never,
        load_queue=never,
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
    )


def test_the_settings_of_a_store_are_those_of_the_config_file_of_its_record(
    tmp_path: Path,
) -> None:
    (tmp_path / FILE).write_text(ENABLED, encoding="utf-8")
    assert open_files(tmp_path).load_settings() == SETTINGS


def test_settings_saved_are_written_as_the_config_file_of_the_record(tmp_path: Path) -> None:
    open_files(tmp_path).save_settings(SETTINGS)
    assert (tmp_path / FILE).read_text(encoding="utf-8") == ENABLED


def test_settings_saved_change_the_config_file_alone(tmp_path: Path) -> None:
    store = open_files(tmp_path)
    store.save_settings(SETTINGS)
    assert store.find_changed_files() == [tmp_path / FILE]


def test_settings_saved_as_the_file_writes_them_change_no_file(tmp_path: Path) -> None:
    (tmp_path / FILE).write_text(ENABLED, encoding="utf-8")
    store = open_files(tmp_path)
    store.save_settings(SETTINGS)
    assert store.find_changed_files() == []


def test_a_config_file_saved_is_put_back_as_it_was(tmp_path: Path) -> None:
    (tmp_path / FILE).write_text(ENABLED, encoding="utf-8")
    store = open_files(tmp_path)
    store.save_settings(LIMITED)
    store.restore_files()
    assert (tmp_path / FILE).read_text(encoding="utf-8") == ENABLED


def test_a_config_file_made_by_a_save_is_removed_when_put_back(tmp_path: Path) -> None:
    store = open_files(tmp_path)
    store.save_settings(SETTINGS)
    store.restore_files()
    assert list(tmp_path.iterdir()) == []


def test_settings_refused_change_no_file(tmp_path: Path) -> None:
    store = open_files(tmp_path)
    with pytest.raises(ConfigError):
        store.save_settings({"development": {"parallel": 0}})
    assert store.find_changed_files() == []


def test_a_store_built_without_settings_holds_none() -> None:
    assert without_settings().load_settings() == {}


def test_a_store_built_without_settings_takes_none() -> None:
    with pytest.raises(NoSettingsStoreError, match=r"^this store keeps no settings$"):
        without_settings().save_settings(SETTINGS)
