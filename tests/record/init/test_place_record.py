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
