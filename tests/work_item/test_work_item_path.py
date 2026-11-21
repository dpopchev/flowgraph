"""The path of a work item file: one rule, the id of the item under `items/` of the record."""

from pathlib import Path

import pytest

from flowgraph.work_item import make_kind, make_work_item_id, work_item_path

pytestmark = pytest.mark.view

CHORE = make_kind("Chore", "a", "CH")


def test_the_file_of_a_work_item_is_named_by_its_id_under_the_items_of_the_record() -> None:
    assert work_item_path(Path("/src/.fgraph"), make_work_item_id(CHORE, 7)) == Path(
        "/src/.fgraph/items/CH-0007.toml"
    )
