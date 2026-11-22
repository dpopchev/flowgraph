"""The journal of a store, on files in a temporary directory: what it notes, names and puts back."""

from pathlib import Path

import pytest

from flowgraph.record.journal import Change, changed_files, noted, restore

pytestmark = pytest.mark.edge


@pytest.fixture
def file(tmp_path: Path) -> Path:
    """A file holding `before`."""
    path = tmp_path / "item.toml"
    path.write_bytes(b"before\n")
    return path


def test_a_file_is_noted_with_its_content_before_the_write(file: Path) -> None:
    assert noted([], file) == [Change(file, b"before\n")]


def test_a_file_that_is_not_there_is_noted_without_content(tmp_path: Path) -> None:
    assert noted([], tmp_path / "new.toml") == [Change(tmp_path / "new.toml", None)]


def test_a_file_noted_twice_keeps_the_content_before_its_first_write(file: Path) -> None:
    journal = noted([], file)
    file.write_bytes(b"after\n")
    assert noted(journal, file) == [Change(file, b"before\n")]


def test_a_file_written_since_it_was_noted_is_named_as_changed(file: Path) -> None:
    journal = noted([], file)
    file.write_bytes(b"after\n")
    assert changed_files(journal) == [file]


def test_a_file_left_as_it_was_noted_is_not_named(file: Path) -> None:
    journal = noted([], file)
    file.write_bytes(b"before\n")
    assert changed_files(journal) == []


def test_a_file_created_since_it_was_noted_is_named_as_changed(tmp_path: Path) -> None:
    journal = noted([], tmp_path / "new.toml")
    (tmp_path / "new.toml").write_bytes(b"after\n")
    assert changed_files(journal) == [tmp_path / "new.toml"]


def test_a_file_changed_is_put_back_as_it_was_noted(file: Path) -> None:
    journal = noted([], file)
    file.write_bytes(b"after\n")
    restore(journal)
    assert file.read_bytes() == b"before\n"


def test_a_file_that_was_not_there_is_removed_again(tmp_path: Path) -> None:
    journal = noted([], tmp_path / "new.toml")
    (tmp_path / "new.toml").write_bytes(b"after\n")
    restore(journal)
    assert not (tmp_path / "new.toml").exists()


def test_a_file_never_written_is_left_absent(tmp_path: Path) -> None:
    journal = noted([], tmp_path / "new.toml")
    restore(journal)
    assert not (tmp_path / "new.toml").exists()
