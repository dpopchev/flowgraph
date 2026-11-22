"""The criterion of noting a finding: `fgraph show` lists it under Knowledge with kind and date."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import Store, run
from flowgraph.queue import make_queue
from flowgraph.story import (
    StoryId,
    StoryNotFoundError,
    StoryState,
    story_detail,
    story_id_text,
    story_row,
)
from flowgraph.task import task_id_text

pytestmark = pytest.mark.functional

CWD = Path("/work")
NOW = datetime(2026, 1, 1, tzinfo=UTC)
ADD_STORY = [
    *("add", "story", "a title"),
    *("--given", "a state", "--when", "an action", "--then", "another"),
]
NOTE = ["note", "S-0001", "--finding", "the file holds it"]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], saved: dict[str, StoryState]) -> Outcome:
    """Run the command in CWD on a record whose stories are the ones saved so far, by id."""

    def held(story_id: StoryId) -> StoryState:
        if story_id_text(story_id) not in saved:
            raise StoryNotFoundError(story_id)
        return saved[story_id_text(story_id)]

    out: list[str] = []
    err: list[str] = []
    status = run(
        argv,
        CWD,
        lambda path: path == CWD / ".fgraph",
        out.append,
        err.append,
        open_store=lambda _: Store(
            find_work_item_rows=lambda kind: [
                story_row(story) for story in saved.values() if story.id.kind == kind
            ],
            load_work_item=held,
            find_work_item_detail=lambda story_id: story_detail(held(story_id)),
            find_task_ids=lambda: [
                task_id_text(task.id) for story in saved.values() for task in story.tasks
            ],
            save_work_item=lambda story: saved.__setitem__(story_id_text(story.id), story),
            load_queue=lambda: make_queue([]),
            save_queue=lambda _: None,
            find_changed_files=lambda: [],
            restore_files=lambda: None,
        ),
        open_git=lambda _: None,
        now=lambda: NOW,
    )
    return Outcome(status, "".join(out), "".join(err))


def test_a_finding_noted_on_a_story_exits_with_zero() -> None:
    saved: dict[str, StoryState] = {}
    fgraph(ADD_STORY, saved)
    assert fgraph(NOTE, saved).status == 0


def test_a_finding_noted_on_a_story_is_listed_under_knowledge_by_show() -> None:
    saved: dict[str, StoryState] = {}
    fgraph(ADD_STORY, saved)
    fgraph(NOTE, saved)
    assert fgraph(["show", "S-0001"], saved).out.endswith(
        "Tasks (0)\nKnowledge (1)\n  finding  2026-01-01  the file holds it\n"
    )
