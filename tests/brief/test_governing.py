"""Which knowledge lines govern a path a Task of a work item names, as a whole path."""

from datetime import UTC, datetime

import pytest

from flowgraph.brief.model import governing
from flowgraph.knowledge.list import KnowledgeEntry
from flowgraph.task.model import TaskRow

pytestmark = pytest.mark.view

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def line(item: str, *governs: str) -> KnowledgeEntry:
    return KnowledgeEntry(item, "decision", NOW, "a text", governs=list(governs))


def task(expected_output: str, description: str = "") -> TaskRow:
    return TaskRow("T-0001", "a title", expected_output, description, "backlog")


def kept(entries: list[KnowledgeEntry], tasks: list[TaskRow]) -> list[str]:
    return [entry.item for entry in governing(entries, tasks)]


def test_a_line_governs_when_the_expected_output_of_a_task_names_its_path() -> None:
    assert kept([line("S-0001", "src/gate.py")], [task("changed: src/gate.py holds")]) == ["S-0001"]


def test_a_line_governs_when_the_description_of_a_task_names_its_path() -> None:
    assert kept([line("S-0001", "src/gate.py")], [task("an output", "edit src/gate.py.")]) == [
        "S-0001"
    ]


def test_a_path_inside_a_longer_path_is_not_named() -> None:
    assert kept([line("S-0001", "src/gate.py")], [task("changed: tests/src/gate.py")]) == []


def test_a_path_with_a_longer_name_is_not_named() -> None:
    assert kept([line("S-0001", "src/gate.py")], [task("changed: src/gate.pyi")]) == []


def test_a_line_that_governs_nothing_a_task_names_is_left_out() -> None:
    assert kept([line("S-0001", "src/other.py"), line("S-0002")], [task("src/gate.py")]) == []


def test_a_line_with_one_path_named_among_several_governs() -> None:
    entries = [line("S-0001", "src/other.py", "src/gate.py")]
    assert kept(entries, [task("changed: src/gate.py")]) == ["S-0001"]


def test_the_lines_keep_the_order_they_were_given_in() -> None:
    entries = [line("S-0002", "src/gate.py"), line("S-0001", "src/gate.py")]
    assert kept(entries, [task("changed: src/gate.py")]) == ["S-0002", "S-0001"]
