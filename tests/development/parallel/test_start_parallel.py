"""The start of a work item within `development.parallel`: what the check lets pass and names.

The start of a Feature starts one work item, so it is checked as one more.
"""

from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.bug import BUG
from flowgraph.development.parallel import ParallelError, check_feature_parallel, check_parallel
from flowgraph.parent import make_feature_id
from flowgraph.record import Config, make_config
from flowgraph.spike import SPIKE
from flowgraph.story import STORY
from flowgraph.upkeep import UPKEEP
from flowgraph.work_item import Kind, WorkItemRow

pytestmark = pytest.mark.command

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
F1 = make_feature_id(1)
ROWS = {
    STORY: [
        WorkItemRow("S-0001", "a started story", "started", created=CREATED, started=CREATED),
        WorkItemRow("S-0002", "a story", "backlog", created=CREATED),
        WorkItemRow("S-0003", "a done story", "completed", "abc1234", created=CREATED),
        WorkItemRow("S-0004", "a removed story", "removed", reason="a reason", created=CREATED),
    ],
    UPKEEP: [WorkItemRow("U-0001", "an upkeep", "started", created=CREATED, started=CREATED)],
    BUG: [WorkItemRow("B-0001", "a bug", "started", created=CREATED, started=CREATED)],
    SPIKE: [
        WorkItemRow("Q-0001", "a spike", "started", created=CREATED, started=CREATED),
        WorkItemRow("Q-0002", "another spike", "backlog", created=CREATED),
    ],
}


def never(*_: object) -> Never:
    """The read of the rows, for a start the check passes without counting."""
    raise AssertionError("the check counts the started work items of a limited development alone")


def rows(kind: Kind) -> list[WorkItemRow]:
    """The rows of a record that holds ROWS: four work items started, one of every kind."""
    return ROWS.get(kind, [])


def limited(most: int) -> Config:
    """The configuration of a record with the development on and that many started at once."""
    return make_config(f"[development]\nenabled = true\nparallel = {most}\n")


@pytest.mark.parametrize("most", [1, 4], ids=["beyond", "as-many"])
def test_a_start_beside_as_many_started_as_parallel_names_each_of_every_kind(most: int) -> None:
    with pytest.raises(ParallelError) as error:
        check_parallel("S-0002", rows, limited(most))
    assert str(error.value) == (
        f"S-0002 cannot start: development.parallel = {most},"
        " started already: S-0001, U-0001, B-0001, Q-0001"
    )


def test_a_work_item_of_another_kind_is_refused_as_a_story_is() -> None:
    with pytest.raises(ParallelError, match=r"^Q-0002 cannot start: development\.parallel = 4,"):
        check_parallel("Q-0002", rows, limited(4))


def test_a_start_beside_fewer_started_than_parallel_passes() -> None:
    assert check_parallel("S-0002", rows, limited(5)) is None


def test_a_start_with_parallel_left_out_passes() -> None:
    assert check_parallel("S-0002", never, make_config("[development]\nenabled = true\n")) is None


def test_a_start_with_the_development_off_passes() -> None:
    assert check_parallel("S-0002", never, make_config("[development]\nparallel = 1\n")) is None


def test_a_task_started_passes() -> None:
    assert check_parallel("T-0001", never, limited(1)) is None


def test_a_text_that_is_no_id_passes_to_the_start_that_refuses_it() -> None:
    assert check_parallel("no-id", never, limited(1)) is None


@pytest.mark.parametrize(
    "item",
    ["S-0001", "S-0003", "S-0004", "S-0099"],
    ids=["started", "completed", "removed", "not-in-the-record"],
)
def test_a_work_item_not_in_backlog_passes_to_the_start_that_refuses_it(item: str) -> None:
    assert check_parallel(item, rows, limited(1)) is None


def test_a_feature_started_beside_as_many_started_as_parallel_names_each_of_every_kind() -> None:
    with pytest.raises(ParallelError) as error:
        check_feature_parallel(F1, rows, limited(4))
    assert str(error.value) == (
        "F-0001 cannot start: development.parallel = 4,"
        " started already: S-0001, U-0001, B-0001, Q-0001"
    )


def test_a_feature_started_beside_fewer_started_than_parallel_passes() -> None:
    assert check_feature_parallel(F1, rows, limited(5)) is None


@pytest.mark.parametrize(
    "text",
    ["[development]\nenabled = true\n", "[development]\nparallel = 1\n"],
    ids=["parallel-left-out", "development-off"],
)
def test_a_feature_started_under_no_limit_passes_without_a_read_of_the_rows(text: str) -> None:
    assert check_feature_parallel(F1, never, make_config(text)) is None
