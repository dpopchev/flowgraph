"""The id of an item of any kind: a Story id, an Upkeep id or a Task id, told apart by its text."""

import pytest

from flowgraph.item import ItemIdError, parse_item_id
from flowgraph.story import make_story_id
from flowgraph.task import make_task_id
from flowgraph.upkeep import make_upkeep_id

pytestmark = pytest.mark.edge


@pytest.mark.parametrize(
    ("text", "item"),
    [("ST-0003", make_story_id(3)), ("U-0002", make_upkeep_id(2)), ("T-0012", make_task_id(12))],
    ids=["story", "upkeep", "task"],
)
def test_an_item_id_is_read_as_the_id_of_its_kind(text: str, item: object) -> None:
    assert parse_item_id(text) == item


@pytest.mark.parametrize("text", ["B-0001", "ST-0000"], ids=["no-kind", "below-one"])
def test_a_text_that_is_no_id_of_any_kind_is_refused_by_itself(text: str) -> None:
    with pytest.raises(ItemIdError, match=f"^'{text}' is no Story, Upkeep or Task id$"):
        parse_item_id(text)
