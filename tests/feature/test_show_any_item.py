"""The format of show is chosen before the record is read: a bad word reads nothing."""

from typing import Never

import pytest

from flowgraph.feature.item import show_any_item
from flowgraph.record.store import FeatureStore, Store, TermStore
from flowgraph.status.show_document import ShowFormatError

pytestmark = pytest.mark.view


def never(*_: object) -> Never:
    """A read or a write of the record that a refused format never asks for."""
    raise AssertionError("the format is chosen before anything is read")


def unread() -> Store:
    """A store whose every read and write fails the test."""
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
        features=FeatureStore(never, never, never),
        terms=TermStore(never, never, never),
    )


@pytest.mark.parametrize("item", ["S-0001", "F-0001", "gate"])
def test_a_format_that_is_neither_is_refused_before_the_record_is_read(item: str) -> None:
    with pytest.raises(
        ShowFormatError, match="--format 'xml' is not text or json, the two formats of show"
    ):
        show_any_item(item, unread(), "xml")
