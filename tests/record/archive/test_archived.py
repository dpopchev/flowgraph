"""An id of board 1 asked of a record that points at its archive: found by the id it held."""

from pathlib import Path

import pytest

from flowgraph.record.archive import (
    UNARCHIVED,
    Archive,
    Archived,
    ArchivedError,
    check_archived,
    old_id,
)

pytestmark = pytest.mark.model

RECORD = Path("/src/project/.fgraph")
LINE = (
    "{old} is in the archive of board 1 at {where} -- show it with: "
    "uv run ~/.claude/skills/board/scripts/board.py --root {root} show {old}"
)


def refused(text: str, archive: Archive, record: Path) -> str:
    """The message check_archived raises for the text."""
    with pytest.raises(ArchivedError) as error:
        check_archived(text, archive, record)
    return str(error.value)


@pytest.mark.parametrize(
    ("text", "old"),
    [
        ("W-123", "W-123"),
        ("E-007", "E-007"),
        ("T-0456", "T-456"),
        ("T-0001", "T-001"),
        ("T-1364", "T-1364"),
        ("w-7", "W-007"),
        ("e-0007", "E-007"),
        ("W-12345", "W-12345"),
    ],
)
def test_an_id_of_board_1_is_written_as_board_1_writes_it(text: str, old: str) -> None:
    assert old_id(text) == old


@pytest.mark.parametrize(
    "text",
    [
        *("W-0", "E-000", "w123", "e7", "S-0001", "F-0001", "X-123", "W-", "W-12a", "W-1-2"),
        *("a-term-name", ""),
    ],
)
def test_a_text_that_is_no_id_of_board_1_has_no_old_id(text: str) -> None:
    assert old_id(text) is None


def test_a_work_item_asked_is_named_at_the_archive_with_the_command_that_shows_it() -> None:
    assert refused("W-123", Archived(".board"), RECORD) == LINE.format(
        old="W-123", where="/src/project/.board", root="/src/project"
    )


def test_a_task_read_as_four_digits_is_named_as_board_1_wrote_it() -> None:
    assert refused("T-0456", Archived(".board"), RECORD) == LINE.format(
        old="T-456", where="/src/project/.board", root="/src/project"
    )


def test_an_absolute_pointer_stays_itself() -> None:
    assert refused("W-123", Archived("/old/.board"), RECORD) == LINE.format(
        old="W-123", where="/old/.board", root="/old"
    )


def test_a_record_with_no_parent_names_the_board_beside_it() -> None:
    assert refused("W-123", Archived(".board"), Path(".fgraph")) == LINE.format(
        old="W-123", where=".board", root="."
    )


def test_a_root_with_a_space_is_quoted_for_the_shell() -> None:
    message = refused("W-123", Archived(".board"), Path("/src/my project/.fgraph"))
    assert message.endswith("--root '/src/my project' show W-123")


def test_a_record_that_points_at_no_archive_refuses_nothing() -> None:
    assert check_archived("W-123", UNARCHIVED, RECORD) is None


@pytest.mark.parametrize("text", ["S-0001", "w123", "a-term-name"])
def test_a_text_that_is_no_id_of_board_1_is_not_refused_under_a_pointer(text: str) -> None:
    assert check_archived(text, Archived(".board"), RECORD) is None
