"""The decision of a completed Spike as a knowledge entry, with its answer when it holds one."""

from datetime import UTC, datetime

import pytest

from flowgraph.knowledge.list import decision_entries
from flowgraph.work_item import WorkItemDetail

pytestmark = pytest.mark.view

DONE = datetime(2026, 1, 5, tzinfo=UTC)


def spike(answer: str) -> WorkItemDetail:
    return WorkItemDetail(
        "Q-0001", "a title", "Completed", "", [], decision="too big", answer=answer
    )


def test_the_entry_of_an_answered_decision_names_the_answer_beside_its_text() -> None:
    assert [entry.text for entry in decision_entries(spike("no"), DONE)] == ["too big (answer no)"]


def test_the_entry_of_a_decision_held_without_an_answer_is_its_text_alone() -> None:
    assert [entry.text for entry in decision_entries(spike(""), DONE)] == ["too big"]
