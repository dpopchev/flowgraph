"""The JSON documents of fgraph show of a work item and of a Feature.

A second formatter of the plain data the text of status/show.py words: no fact is computed but
the kind, read from the prefix of the id, and the buckets, read from the states; a key that holds
nothing is null, a list that holds nothing is empty. The keys are sorted and the text ends with
a newline, so two runs on one record print the same bytes (S-0154).
"""

import json
from collections.abc import Iterable
from typing import Any

from flowgraph.feature import FeatureDetail, criteria_rows
from flowgraph.knowledge import KnowledgeRow
from flowgraph.record.store import KINDS
from flowgraph.status.buckets import BUCKETS
from flowgraph.task import TaskRow
from flowgraph.work_item import ProgressRow, WorkItemDetail, WorkItemRow

# The two formats of show; the first is the default.
TEXT = "text"
JSON = "json"

type Part = dict[str, Any]


class ShowFormatError(ValueError):
    """A format of show that is none there is."""


def chosen_show_format(format_: str) -> str:
    """The format of show asked for.

    Raises ShowFormatError naming the word and the two formats when it is neither.
    """
    if format_ not in (TEXT, JSON):
        raise ShowFormatError(
            f"--format {format_!r} is not {TEXT} or {JSON}, the two formats of show"
        )
    return format_


def _bucket(state: str) -> str:
    """The bucket a state is listed in."""
    return next(name for name, states in BUCKETS if state in states)


def _line(row: KnowledgeRow) -> Part:
    """A knowledge line with all its parts; the mark is null when it has none."""
    return {
        "about": list(row.about),
        "governs": list(row.governs),
        "kind": row.kind,
        "mark": row.mark or None,
        "noted": row.noted.isoformat(),
        "superseded_by": list(row.superseded_by),
        "supersedes": list(row.supersedes),
        "text": row.text,
    }


def _progress(lines: Iterable[ProgressRow]) -> list[Part]:
    """The progress lines, each with its time and its text."""
    return [{"noted": line.noted.isoformat(), "text": line.text} for line in lines]


def _task(task: TaskRow, progress: Iterable[ProgressRow]) -> Part:
    """A Task with its bucket and its own progress lines; an empty text is null."""
    return {
        "bucket": _bucket(task.state),
        "check": task.check or None,
        "commit": task.commit or None,
        "description": task.description or None,
        "expected_output": task.expected_output or None,
        "id": task.id,
        "progress": _progress(line for line in progress if line.task == task.id),
        "reason": task.reason or None,
        "state": task.state,
        "title": task.title,
        "waiting_on": task.waiting_on or None,
    }


def _criterion(detail: WorkItemDetail) -> Part:
    """The parts of the criterion of every kind; those its kind does not state are null."""
    return {
        "answer": detail.answer or None,
        "decision": detail.decision or None,
        "expected": detail.expected or None,
        "given": detail.given or None,
        "hypothesis": detail.hypothesis or None,
        "observed": detail.observed or None,
        "then": detail.then or None,
        "when": detail.when or None,
    }


def _verified(detail: WorkItemDetail) -> Part | None:
    """The answer of the closing with its time and text; null before it."""
    answer = detail.verified
    if answer is None:
        return None
    return {"answer": answer.answer, "on": answer.on.isoformat(), "text": answer.text}


def _canonical(document: Part) -> str:
    """The document as text: sorted keys, an indent of two and a newline."""
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def work_item_json(detail: WorkItemDetail) -> str:
    """The work item as a JSON document: every part its text lists, each under a stable key."""
    kinds = {kind.prefix: kind.noun.lower() for kind in KINDS}
    own = [line for line in detail.progress if line.task == ""]
    return _canonical(
        {
            "about": list(detail.about),
            "agent": detail.agent or None,
            "amended_by": list(detail.amended_by),
            "amends": detail.amends or None,
            "bucket": _bucket(detail.state),
            "commit": detail.commit or None,
            "complexity": detail.complexity or None,
            "criterion": _criterion(detail),
            "depends_on": [
                {"bucket": each.bucket or None, "id": each.id} for each in detail.depends_on
            ],
            "description": detail.description or None,
            "filed_during": detail.filed_during or None,
            "filed_here": list(detail.filed_here),
            "id": detail.id,
            "kind": kinds[detail.id.partition("-")[0]],
            "knowledge": [_line(line) for line in detail.knowledge],
            "parent": detail.parent or None,
            "progress": _progress(own),
            "realized": detail.realized or None,
            "realizes": detail.realizes,
            "reason": detail.reason or None,
            "state": detail.state,
            "superseded_by": detail.superseded_by or None,
            "supersedes": list(detail.supersedes),
            "tasks": [_task(task, detail.progress) for task in detail.tasks],
            "title": detail.title,
            "verified": _verified(detail),
            "waiting_on": detail.waiting_on or None,
        }
    )


def feature_json(detail: FeatureDetail, rows: Iterable[WorkItemRow], bucket: str) -> str:
    """The Feature as a JSON document: every part its text lists, each under a stable key."""
    listed = list(rows)
    return _canonical(
        {
            "about": list(detail.about),
            "bucket": bucket,
            "commit": detail.commit or None,
            "criteria": [
                {
                    "met": row.met,
                    "number": row.number,
                    "realized_by": list(row.realized_by),
                    "text": row.text,
                }
                for row in criteria_rows(detail.criteria, listed)
            ],
            "description": detail.description or None,
            "id": detail.id,
            "kind": "feature",
            "knowledge": [_line(line) for line in detail.knowledge],
            "reason": detail.reason or None,
            "title": detail.title,
            "waiting_on": detail.waiting_on or None,
            "work_items": [
                {"bucket": _bucket(row.state), "id": row.id, "title": row.title} for row in listed
            ],
        }
    )
