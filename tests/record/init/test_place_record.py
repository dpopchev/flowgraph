"""Where fgraph init puts the record: `.fgraph/` in the directory, unless one is held there."""

from collections.abc import Collection
from pathlib import Path

import pytest

from flowgraph.record.init import NoDirectoryError, RecordHeldError, place_record

pytestmark = pytest.mark.model

CWD = Path("/work")


def dirs(*paths: str) -> Collection[Path]:
    """The directories that exist, as absolute paths."""
    return {Path(path) for path in paths}


def test_puts_the_record_in_the_directory_it_runs_in() -> None:
    assert place_record(CWD, None, dirs().__contains__) == CWD / ".fgraph"


def test_puts_the_record_in_the_directory_given() -> None:
    other = CWD / "other"
    assert place_record(CWD, other, dirs("/work/other").__contains__) == other / ".fgraph"


def test_refuses_a_directory_that_holds_the_dot_directory() -> None:
    with pytest.raises(RecordHeldError, match=r"/work/\.fgraph holds a record already"):
        place_record(CWD, None, dirs("/work/.fgraph").__contains__)


def test_refuses_a_directory_that_holds_the_plain_directory() -> None:
    with pytest.raises(RecordHeldError, match=r"/work/fgraph holds a record already"):
        place_record(CWD, None, dirs("/work/fgraph").__contains__)


def test_refuses_a_directory_given_that_is_none() -> None:
    with pytest.raises(NoDirectoryError, match="--dir /work/missing is no directory"):
        place_record(CWD, CWD / "missing", dirs().__contains__)


NAMED = CWD / ".dpopchev"


def test_puts_the_record_in_the_folder_the_key_names() -> None:
    assert place_record(CWD, None, dirs("/work").__contains__, NAMED) == NAMED


def test_puts_the_record_in_the_folder_named_though_the_dot_directory_is_held() -> None:
    assert place_record(CWD, None, dirs("/work", "/work/.fgraph").__contains__, NAMED) == NAMED


def test_refuses_a_folder_named_that_is_a_directory() -> None:
    with pytest.raises(RecordHeldError, match=r"^/work/\.dpopchev holds a record already$"):
        place_record(CWD, None, dirs("/work", "/work/.dpopchev").__contains__, NAMED)


def test_refuses_a_folder_named_whose_parent_is_no_directory() -> None:
    named = Path("/work/local/record")
    line = r"^git config fgraph\.record names /work/local/record, but /work/local is no directory$"
    with pytest.raises(NoDirectoryError, match=line):
        place_record(CWD, None, dirs("/work").__contains__, named)


def test_puts_the_record_in_the_directory_given_whatever_is_named() -> None:
    other = CWD / "other"
    assert place_record(CWD, other, dirs("/work/other").__contains__, NAMED) == other / ".fgraph"
