"""The node of a Task in the graph: its bucket as fgraph show lists it, and its state."""

import pytest

from flowgraph.graph.view import task_node
from flowgraph.task import TaskRow

pytestmark = pytest.mark.view


def task(state: str) -> TaskRow:
    """A Task in that state."""
    return TaskRow("T-0001", "a task", "an output", "", state)


@pytest.mark.parametrize(
    ("state", "bucket"),
    [
        ("backlog", "Backlog"),
        ("started", "InProgress"),
        ("blocked", "InProgress"),
        ("completed", "Completed"),
    ],
)
def test_a_task_node_is_in_the_bucket_its_state_is_listed_in(state: str, bucket: str) -> None:
    assert task_node(task(state), "started")["bucket"] == bucket


@pytest.mark.parametrize("state", ["backlog", "started", "blocked", "completed"])
def test_a_task_node_carries_its_state_in_the_words_of_status(state: str) -> None:
    assert task_node(task(state), "started")["state"] == state


@pytest.mark.parametrize("state", ["backlog", "started", "blocked", "completed"])
def test_a_task_of_a_removed_work_item_is_in_removed_with_its_state_kept(state: str) -> None:
    node = task_node(task(state), "removed")
    assert (node["bucket"], node["state"]) == ("Removed", state)


def test_a_task_node_keeps_its_id_its_kind_and_its_title_in_the_first_keys() -> None:
    assert list(task_node(task("backlog"), "backlog").items())[:3] == [
        ("id", "T-0001"),
        ("kind", "task"),
        ("title", "a task"),
    ]
