"""The format of about is chosen before the record or git is read: a refused one reads nothing."""

from pathlib import Path
from typing import Never

import pytest

from flowgraph.about.document import AboutFormatError
from flowgraph.about.view import about_item
from flowgraph.record.queue import make_queue
from flowgraph.record.store import FeatureStore, Store, TermStore

pytestmark = pytest.mark.view


def never(*_: object) -> Never:
    """A read or a write of the record or of git that a refused format never asks for."""
    raise AssertionError("a format that is refused reads nothing")


STORE = Store(
    find_work_item_rows=never,
    load_work_item=never,
    find_work_item_detail=never,
    find_task_ids=never,
    save_work_item=never,
    load_queue=lambda: make_queue([]),
    save_queue=never,
    find_changed_files=never,
    restore_files=never,
    features=FeatureStore(never, never, never),
    terms=TermStore(never, never, never),
)


@pytest.mark.parametrize("item", ["S-0001", "F-0001", "gate", "work.txt"])
def test_a_format_that_is_neither_is_refused_before_anything_is_read(item: str) -> None:
    with pytest.raises(
        AboutFormatError, match="--format 'xml' is not text or json, the two formats of about"
    ):
        about_item(item, STORE, Path("/w"), never, "xml")
