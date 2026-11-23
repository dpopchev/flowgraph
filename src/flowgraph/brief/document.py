"""The JSON document of the brief of a work item.

A second formatter of the brief beside its text: no fact is computed here but the kind, which is
read from the prefix of the id, the bucket, which is read from the state, and the ids it waits
for, which are those it depends on that are not completed. A key that holds nothing is null,
and a list that holds nothing is empty. The keys are sorted and the text ends with a newline,
so two runs on one record print the same bytes.
"""

import json
from collections.abc import Iterable
from typing import Any

from flowgraph.brief.model import Brief, FeatureBrief
from flowgraph.knowledge.list import KnowledgeEntry
from flowgraph.knowledge.model import KnowledgeRow
from flowgraph.record.store import KINDS
from flowgraph.status.text import BUCKETS
from flowgraph.task.model import TaskRow
from flowgraph.work_item.views import WorkItemDetail

# The two formats of brief; the first is the default.
TEXT = "text"
JSON = "json"

# The bucket a dependency is listed in once it is done.
_COMPLETED = "Completed"

type Part = dict[str, Any]


class BriefFormatError(ValueError):
    """A format of brief that is none there is."""


def chosen_brief_format(format_: str) -> str:
    """The format of brief asked for.

    Raises BriefFormatError naming the word and the two formats when it is neither.
    """
    if format_ not in (TEXT, JSON):
        raise BriefFormatError(
            f"--format {format_!r} is not {TEXT} or {JSON}, the two formats of brief"
        )
    return format_


def _line(row: KnowledgeRow | KnowledgeEntry) -> Part:
    """A knowledge line with its kind, its time, its text, the terms it is about and its files."""
    return {
        "kind": row.kind,
        "noted": row.noted.isoformat(),
        "text": row.text,
        "about": list(row.about),
        "governs": list(row.governs),
    }


def _task(task: TaskRow) -> Part:
    """A Task with its parts; an empty one is null."""
    return {
        "id": task.id,
        "title": task.title,
        "state": task.state,
        "expected_output": task.expected_output or None,
        "check": task.check or None,
        "description": task.description or None,
        "commit": task.commit or None,
        "reason": task.reason or None,
        "waiting_on": task.waiting_on or None,
    }


def _criterion(detail: WorkItemDetail) -> Part:
    """The parts of the criterion of every kind; those its kind does not state are null."""
    return {
        "given": detail.given or None,
        "when": detail.when or None,
        "then": detail.then or None,
        "observed": detail.observed or None,
        "expected": detail.expected or None,
        "hypothesis": detail.hypothesis or None,
        "decision": detail.decision or None,
        "answer": detail.answer or None,
    }


def _feature(feature: FeatureBrief | None) -> Part | None:
    """The Feature with its knowledge; null for a work item that stands alone."""
    if feature is None:
        return None
    return {
        "id": feature.id,
        "title": feature.title,
        "bucket": feature.bucket,
        "description": feature.description or None,
        "knowledge": [_line(line) for line in feature.knowledge],
    }


def _governing(entries: Iterable[KnowledgeEntry]) -> list[Part]:
    """The lines that govern, each with the id of the item that holds it."""
    return [{"item": entry.item, **_line(entry)} for entry in entries]


def brief_json(brief: Brief) -> str:
    """The brief as a JSON document: the work item whole, then what the brief adds to it."""
    detail = brief.detail
    kinds = {kind.prefix: kind.noun.lower() for kind in KINDS}
    document = {
        "id": detail.id,
        "kind": kinds[detail.id.partition("-")[0]],
        "title": detail.title,
        "state": detail.state,
        "bucket": next(name for name, states in BUCKETS if detail.state in states),
        "agent": detail.agent or None,
        "complexity": detail.complexity or None,
        "description": detail.description or None,
        "criterion": _criterion(detail),
        "depends_on": [{"id": each.id, "bucket": each.bucket} for each in detail.depends_on],
        "waits_for": [each.id for each in detail.depends_on if each.bucket != _COMPLETED],
        "tasks": [_task(task) for task in detail.tasks],
        "knowledge": [_line(line) for line in detail.knowledge],
        "branch": brief.branch,
        "worktree": None if brief.worktree is None else str(brief.worktree),
        "feature": _feature(brief.feature),
        "governed_by": _governing(brief.governed_by),
        "terms": [{"name": term.name, "meaning": term.meaning} for term in brief.terms],
    }
    return json.dumps(document, indent=2, sort_keys=True) + "\n"
