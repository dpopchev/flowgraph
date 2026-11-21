"""The id of an item of any kind: a Story id, an Upkeep id or a Task id, told apart by its text."""

import pytest

from flowgraph.item import ItemIdError, parse_item_id, parse_work_item_id_of_any_kind
from flowgraph.story import make_story_id
from flowgraph.task import make_task_id
from flowgraph.upkeep import make_upkeep_id
from flowgraph.work_item import WorkItemIdError

pytestmark = pytest.mark.edge


@pytest.mark.parametrize(
    ("text", "item"),
    [("S-0003", make_story_id(3)), ("U-0002", make_upkeep_id(2)), ("T-0012", make_task_id(12))],
    ids=["story", "upkeep", "task"],
)
def test_an_item_id_is_read_as_the_id_of_its_kind(text: str, item: object) -> None:
    assert parse_item_id(text) == item


@pytest.mark.parametrize("text", ["X-0001", "S-0000"], ids=["no-kind", "below-one"])
def test_a_text_that_is_no_id_of_any_kind_is_refused_by_itself(text: str) -> None:
    with pytest.raises(ItemIdError, match=f"^'{text}' is no Story, Upkeep, Bug, Spike or Task id$"):
        parse_item_id(text)


@pytest.mark.parametrize(
    "text", ["F-0001", "T-0001", "S-0000"], ids=["a-feature", "a-task", "below-one"]
)
def test_a_text_that_is_no_work_item_id_of_any_kind_is_refused_naming_every_kind(
    text: str,
) -> None:
    with pytest.raises(WorkItemIdError, match=f"^'{text}' is no Story, Upkeep, Bug or Spike id$"):
        parse_work_item_id_of_any_kind(text)
