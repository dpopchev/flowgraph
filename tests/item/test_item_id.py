"""The id of an item of any kind: a Story id, an Upkeep id or a Task id, told apart by its text."""

import pytest

from flowgraph.bug import make_bug_id
from flowgraph.item import ItemIdError, parse_item_id, parse_work_item_id_of_any_kind
from flowgraph.item_id import parse_moved_id, parse_placed_id, parse_shown_id
from flowgraph.parent import FeatureIdError, make_feature_id
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
    named = f"^'{text}' is no Story, Upkeep, Bug, Spike, Task or Feature id$"
    with pytest.raises(ItemIdError, match=named):
        parse_item_id(text)


@pytest.mark.parametrize(
    "text", ["F-0001", "T-0001", "S-0000"], ids=["a-feature", "a-task", "below-one"]
)
def test_a_text_that_is_no_work_item_id_of_any_kind_is_refused_naming_every_kind(
    text: str,
) -> None:
    with pytest.raises(WorkItemIdError, match=f"^'{text}' is no Story, Upkeep, Bug or Spike id$"):
        parse_work_item_id_of_any_kind(text)


@pytest.mark.parametrize(
    ("text", "placed"),
    [("U-0002", make_upkeep_id(2)), ("F-0003", make_feature_id(3))],
    ids=["upkeep", "feature"],
)
def test_an_id_the_queue_places_is_read_as_that_of_a_work_item_or_of_a_feature(
    text: str, placed: object
) -> None:
    assert parse_placed_id(text) == placed


@pytest.mark.parametrize("text", ["T-0001", "F-0000"], ids=["a-task", "below-one"])
def test_a_text_that_is_no_id_the_queue_places_is_refused_naming_every_kind_and_the_feature(
    text: str,
) -> None:
    with pytest.raises(
        ItemIdError, match=f"^'{text}' is no Story, Upkeep, Bug, Spike or Feature id$"
    ):
        parse_placed_id(text)


@pytest.mark.parametrize(
    ("text", "shown"),
    [("B-0002", make_bug_id(2)), ("F-0003", make_feature_id(3))],
    ids=["bug", "feature"],
)
def test_an_id_show_takes_is_read_as_that_of_a_work_item_or_of_a_feature(
    text: str, shown: object
) -> None:
    assert parse_shown_id(text) == shown


@pytest.mark.parametrize(
    "text", ["X-0001", "T-0001", "S-0000"], ids=["no-kind", "task", "below-one"]
)
def test_a_text_that_is_no_id_show_takes_is_refused_naming_every_kind_and_the_feature(
    text: str,
) -> None:
    with pytest.raises(
        ItemIdError, match=f"^'{text}' is no Story, Upkeep, Bug, Spike or Feature id$"
    ):
        parse_shown_id(text)


def test_a_feature_id_below_one_show_is_given_is_refused_as_a_feature_id() -> None:
    with pytest.raises(FeatureIdError, match=r"^a Feature id counts from 1: 0 is below 1$"):
        parse_shown_id("F-0000")


@pytest.mark.parametrize(
    ("text", "moved"),
    [("T-0004", make_task_id(4)), ("F-0003", make_feature_id(3))],
    ids=["task", "feature"],
)
def test_an_id_block_takes_is_read_as_that_of_a_task_or_of_a_feature(
    text: str, moved: object
) -> None:
    assert parse_moved_id(text) == moved


@pytest.mark.parametrize("text", ["X-0001", "S-0001"], ids=["no-kind", "a-story"])
def test_a_text_that_is_no_id_block_takes_is_refused_naming_the_task_and_the_feature(
    text: str,
) -> None:
    with pytest.raises(ItemIdError, match=f"^'{text}' is no Task or Feature id$"):
        parse_moved_id(text)


@pytest.mark.parametrize(
    ("text", "why"),
    [("F-0000", "a Feature id counts from 1"), ("T-0000", "a Task id counts from 1")],
    ids=["feature", "task"],
)
def test_an_id_below_one_block_is_given_is_refused_as_one_of_its_kind(text: str, why: str) -> None:
    with pytest.raises(ValueError, match=f"^{why}: 0 is below 1$"):
        parse_moved_id(text)
