"""The file of a work item: its criterion table, and the write that reads itself back.

Its Task tables are in flowgraph.item.task_file.
"""

from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Literal, assert_never

import tomli_w
from pydantic import BaseModel, ConfigDict

from flowgraph.criterion import (
    Commit,
    Criterion,
    Decision,
    Evidence,
    NoCommit,
    criterion_parts,
    make_defect,
    make_hypothesis,
    make_scenario,
)
from flowgraph.knowledge import (
    DECISION,
    DEVIATION,
    FINDING,
    KnowledgeLine,
    kind_name,
    make_knowledge_line,
)


class CriterionFile(BaseModel):
    """The criterion table of a work item file: its Given / When / Then."""

    model_config = ConfigDict(extra="forbid")

    given: str
    when: str
    then: str


class DefectFile(BaseModel):
    """The criterion table of the file of a Bug: what is observed and what is expected."""

    model_config = ConfigDict(extra="forbid")

    observed: str
    expected: str


class HypothesisFile(BaseModel):
    """The criterion table of the file of a Spike not yet completed: its hypothesis."""

    model_config = ConfigDict(extra="forbid")

    hypothesis: str


class AnswerFile(BaseModel):
    """The criterion table of the file of a completed Spike: its hypothesis, decision and answer.

    A file of a Spike completed before the answer was taken holds none.
    """

    model_config = ConfigDict(extra="forbid")

    hypothesis: str
    decision: str
    answer: Literal["yes", "no"] | None = None


# The criterion table of a work item file, in the form its kind takes.
AnyCriterionFile = CriterionFile | DefectFile | HypothesisFile | AnswerFile


class KnowledgeFile(BaseModel):
    """One table of the knowledge of a work item file: a line, with its kind, text and time."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["finding", "decision", "deviation"]
    text: str
    noted: datetime
    about: list[str] = []
    governs: list[str] = []


def knowledge_primitives(line: KnowledgeLine) -> dict[str, object]:
    """The knowledge line as the primitives its table holds, its terms and files when it has any."""
    about = {"about": list(line.about)} if line.about else {}
    governs = {"governs": list(line.governs)} if line.governs else {}
    head = {"kind": kind_name(line.kind), "text": line.text, "noted": line.noted}
    return {**head, **about, **governs}


def knowledge_held(held: KnowledgeFile) -> KnowledgeLine:
    """The knowledge line a validated table holds, built through its constructor."""
    about = tuple(held.about)
    governs = tuple(held.governs)
    match held.kind:
        case "finding":
            return make_knowledge_line(FINDING, held.text, held.noted, about, governs)
        case "decision":
            return make_knowledge_line(DECISION, held.text, held.noted, about, governs)
        case "deviation":
            return make_knowledge_line(DEVIATION, held.text, held.noted, about, governs)
        case _ as unreachable:
            assert_never(unreachable)


def criterion_primitives(criterion: Criterion) -> dict[str, object]:
    """The criterion as the primitives its table holds."""
    return dict(criterion_parts(criterion))


def criterion_held(held: AnyCriterionFile) -> Criterion:
    """The criterion a validated table holds as its work item had it in Backlog.

    Built through its constructor; a hypothesis is held without the decision that answers it,
    which the completion of the work item adds (decision_held).
    """
    match held:
        case CriterionFile():
            return make_scenario(held.given, held.when, held.then)
        case DefectFile():
            return make_defect(held.observed, held.expected)
        case HypothesisFile() | AnswerFile():
            return make_hypothesis(held.hypothesis)
        case _ as unreachable:
            assert_never(unreachable)


def decision_held(held: AnyCriterionFile) -> Decision | None:
    """The decision a validated criterion table holds; None for one without a decision.

    The answer of a table written before it was taken is None.
    """
    match held:
        case AnswerFile():
            return Decision(held.decision, held.answer)
        case CriterionFile() | DefectFile() | HypothesisFile():
            return None
        case _ as unreachable:
            assert_never(unreachable)


def evidence_primitives(evidence: Evidence) -> dict[str, object]:
    """The evidence as the primitives a completed item holds: its commit, or no key for none."""
    match evidence:
        case Commit():
            return {"commit": evidence.sha}
        case NoCommit():
            return {}
        case _ as unreachable:
            assert_never(unreachable)


def write_checked(
    path: Path,
    primitives: Mapping[str, object],
    holds: Callable[[Path], bool],
    mismatch: Exception,
) -> None:
    """Write the primitives as the TOML file at the path, once the written file holds them.

    The file is written beside the path and replaces it only when holds says the written file
    reads back as meant. Raises mismatch otherwise; the file at the path is then as it was.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    beside = path.with_name(f"{path.name}.tmp")
    beside.write_text(tomli_w.dumps(primitives), encoding="utf-8")
    if not holds(beside):
        beside.unlink()
        raise mismatch
    beside.replace(path)
