"""The lock of a record, on directories in a temporary directory: what it holds, refuses and frees.

The wait is the append of a list, so nothing sleeps and the waits are listed.
"""

from pathlib import Path

import pytest

from flowgraph.parser.not_given import no_lock
from flowgraph.record.lock import BEING_WRITTEN, LockedError, lock_files

pytestmark = pytest.mark.edge


def refused(record: Path, tries: int = 1) -> list[float] | None:
    """The waits of a lock of the record tried that many times, or None when it is taken."""
    waited: list[float] = []
    try:
        with lock_files(record, waited.append, tries):
            return None
    except LockedError:
        return waited


def test_the_body_runs_with_the_lock_taken(tmp_path: Path) -> None:
    with lock_files(tmp_path, [].append):
        waited = refused(tmp_path)
    assert waited is not None


def test_after_the_block_the_lock_is_taken_again(tmp_path: Path) -> None:
    with lock_files(tmp_path, [].append):
        pass
    assert refused(tmp_path) is None


def test_a_lock_refused_after_three_tries_has_waited_twice(tmp_path: Path) -> None:
    with lock_files(tmp_path, [].append):
        waited = refused(tmp_path, tries=3)
    assert waited == [0.1, 0.1]


def test_a_lock_refused_after_one_try_has_not_waited(tmp_path: Path) -> None:
    with lock_files(tmp_path, [].append):
        waited = refused(tmp_path, tries=1)
    assert waited == []


def test_the_refusal_names_the_record_being_written(tmp_path: Path) -> None:
    with (
        lock_files(tmp_path, [].append),
        pytest.raises(LockedError) as raised,
        lock_files(tmp_path, [].append, tries=1),
    ):
        pass
    assert str(raised.value) == BEING_WRITTEN.format(record=tmp_path)


def test_the_lock_is_given_back_when_the_body_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError), lock_files(tmp_path, [].append):
        raise ValueError
    assert refused(tmp_path) is None


def test_a_refused_lock_leaves_none_behind(tmp_path: Path) -> None:
    with lock_files(tmp_path, [].append):
        refused(tmp_path)
    assert refused(tmp_path) is None


def test_the_directory_lists_no_file_after_a_take(tmp_path: Path) -> None:
    with lock_files(tmp_path, [].append):
        pass
    assert list(tmp_path.iterdir()) == []


def test_the_locks_of_two_directories_do_not_meet(tmp_path: Path) -> None:
    (tmp_path / "one").mkdir()
    (tmp_path / "two").mkdir()
    with lock_files(tmp_path / "one", [].append):
        waited = refused(tmp_path / "two")
    assert waited is None


def test_no_lock_runs_its_body(tmp_path: Path) -> None:
    ran: list[Path] = []
    with no_lock(tmp_path):
        ran.append(tmp_path)
    assert ran == [tmp_path]
