"""The file of the Backlog queue: `queue.toml` in the record, the ids placed in their order."""

import tomllib
from pathlib import Path

import pytest

from flowgraph import queue as queue_module
from flowgraph.parent import make_feature_id
from flowgraph.queue import (
    QueueFileError,
    QueueMismatchError,
    make_queue,
    read_queue,
    write_queue,
)
from flowgraph.work_item import make_kind, make_work_item_id

pytestmark = pytest.mark.edge

CHORE = make_kind("Chore", "a", "CH")
ERRAND = make_kind("Errand", "an", "ER")
KINDS = (CHORE, ERRAND)
QUEUE = make_queue([make_work_item_id(ERRAND, 2), make_feature_id(1), make_work_item_id(CHORE, 1)])
FILE = "queue.toml"


def test_a_queue_is_written_as_the_ids_of_the_work_items_and_the_features_placed_in_their_order(
    tmp_path: Path,
) -> None:
    write_queue(tmp_path, KINDS, QUEUE)
    written = tomllib.loads((tmp_path / FILE).read_text("utf-8"))
    assert written == {"backlog": ["ER-0002", "F-0001", "CH-0001"]}


def test_a_queue_reads_back_whole(tmp_path: Path) -> None:
    write_queue(tmp_path, KINDS, QUEUE)
    assert read_queue(tmp_path, KINDS) == QUEUE


def test_a_record_without_a_queue_file_holds_the_empty_queue(tmp_path: Path) -> None:
    assert read_queue(tmp_path, KINDS) == make_queue([])


@pytest.mark.parametrize(
    ("content", "why"),
    [
        ("not a queue", "queue.toml holds no queue"),
        (
            'backlog = ["XY-0001"]\n',
            "queue.toml holds no queue: 'XY-0001' is no Chore, Errand or Feature id",
        ),
        (
            'backlog = ["CH-0001", "CH-0001"]\n',
            "queue.toml holds no queue: CH-0001 is placed twice",
        ),
    ],
    ids=["no-toml", "id-of-no-kind", "id-placed-twice"],
)
def test_a_file_that_holds_no_queue_is_refused_naming_it(
    tmp_path: Path, content: str, why: str
) -> None:
    (tmp_path / FILE).write_text(content, encoding="utf-8")
    with pytest.raises(QueueFileError, match=why):
        read_queue(tmp_path, KINDS)


class TestAWriteThatReadsBackDifferent:
    @pytest.fixture
    def failed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str]:
        """The file and the message of a write whose read-back places another work item."""
        path = tmp_path / FILE
        path.write_text("previous", encoding="utf-8")
        monkeypatch.setattr(queue_module.tomllib, "loads", lambda _: {"backlog": ["CH-0009"]})
        with pytest.raises(QueueMismatchError) as error:
            write_queue(tmp_path, KINDS, QUEUE)
        return path, str(error.value)

    def test_keeps_the_previous_content(self, failed: tuple[Path, str]) -> None:
        assert failed[0].read_text(encoding="utf-8") == "previous"

    def test_names_the_path(self, failed: tuple[Path, str]) -> None:
        assert failed[1] == f"{failed[0]}: the queue written reads back different"
