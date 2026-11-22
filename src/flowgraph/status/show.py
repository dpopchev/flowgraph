"""The text fgraph writes for one item whole: a work item with its Tasks, or a Feature."""

from collections.abc import Iterable, Sequence

from flowgraph.feature import FeatureDetail
from flowgraph.knowledge import KnowledgeRow, about_text, governs_text
from flowgraph.status.text import BLOCKED, BUCKETS
from flowgraph.story import StoryDetail, StoryRow
from flowgraph.upkeep import UpkeepDetail, UpkeepRow


def _knowledge_lines(knowledge: Sequence[KnowledgeRow]) -> list[str]:
    """The knowledge lines under their heading, each with its kind, its date and its text.

    There is no heading without a line.
    """
    if not knowledge:
        return []
    return [
        f"Knowledge ({len(knowledge)})\n",
        *(
            f"  {line.kind}  {line.noted.date().isoformat()}  {line.text}"
            f"{about_text(line.about)}{governs_text(line.governs)}\n"
            for line in knowledge
        ),
    ]


def feature_text(detail: FeatureDetail, rows: Iterable[StoryRow | UpkeepRow], bucket: str) -> str:
    """The Feature with its bucket, its criteria, then its work items with their buckets.

    The bucket of a Feature is read from its state and its work items, so it is given; a
    commit and a description are listed only when there is one. A blocked Feature is listed in
    its bucket as blocked, with its reason and what it waits on; a removed one with its reason.
    """
    listed = list(rows)
    committed = [f"  commit       {detail.commit}\n"] if detail.commit else []
    described = [f"  description  {detail.description}\n"] if detail.description else []
    reason = [f"  reason       {detail.reason}\n"] if detail.reason else []
    about = [f"  about        {', '.join(detail.about)}\n"] if detail.about else []
    waited = [f"  waiting on   {detail.waiting_on}\n"] if detail.waiting_on else []
    lines = [
        f"{detail.id}  {detail.title}\n",
        f"  bucket       {bucket}{', blocked' if detail.waiting_on else ''}\n",
        *reason,
        *waited,
        *committed,
        *described,
        *about,
        f"Criteria ({len(detail.criteria)})\n",
        *(f"  {criterion}\n" for criterion in detail.criteria),
        f"Work items ({len(listed)})\n",
    ]
    for row in listed:
        held_in = next(name for name, states in BUCKETS if row.state in states)
        lines.append(f"  {row.id}  {row.title}  {held_in}\n")
    return "".join([*lines, *_knowledge_lines(detail.knowledge)])


def show_text(detail: StoryDetail | UpkeepDetail) -> str:
    """The work item with its bucket and its criterion, then its Tasks, one fact per line.

    The criterion is listed by the parts its kind states: a Given / When / Then, what is
    observed and expected, or a hypothesis with, once it is answered, its decision under it.
    A parent, the work items it depends on each with its bucket, the work item it was filed
    during, the work items filed during it, the work items it supersedes, the completed one it
    amends, the work items that amend it, a description, a commit, the answer of its closing
    with its day and the text the run printed, the work item that supersedes a removed one and
    the reason of a removal are listed only when there is one, the bucket of a
    Task only once it has left Backlog. A blocked Task is listed in InProgress as blocked, with
    its reason and what it waits on. The knowledge lines follow, in the order noted, each with
    its kind, its date and its text, then the terms it is about; there is no heading without one.
    The terms the item is about are listed after its description, only when there are some.
    """
    bucket = next(name for name, states in BUCKETS if detail.state in states)
    under = [f"  parent       {detail.parent}\n"] if detail.parent else []
    waits = ", ".join(f"{each.id} ({each.bucket})" for each in detail.depends_on)
    depends = [f"  depends on   {waits}\n"] if waits else []
    during = [f"  filed during {detail.filed_during}\n"] if detail.filed_during else []
    here = ", ".join(detail.filed_here)
    filed_here = [f"  filed here   {here}\n"] if here else []
    amends = [f"  amends       {detail.amends}\n"] if detail.amends else []
    amending = ", ".join(detail.amended_by)
    amended = [f"  amended by   {amending}\n"] if amending else []
    committed = [f"  commit       {detail.commit}\n"] if detail.commit else []
    answer = detail.verified
    day = None if answer is None else answer.on.date().isoformat()
    verified = [] if answer is None else [f"  verified     {answer.answer}  {day}  {answer.text}\n"]
    removed = [f"  reason       {detail.reason}\n"] if detail.reason else []
    superseded = [f"  superseded by {detail.superseded_by}\n"] if detail.superseded_by else []
    supersedes = ", ".join(detail.supersedes)
    supersede = [f"  supersedes   {supersedes}\n"] if supersedes else []
    described = [f"  description  {detail.description}\n"] if detail.description else []
    about = [f"  about        {', '.join(detail.about)}\n"] if detail.about else []
    stated = {
        "given": detail.given,
        "when": detail.when,
        "then": detail.then,
        "observed": detail.observed,
        "expected": detail.expected,
        "hypothesis": detail.hypothesis,
        "decision": detail.decision,
    }
    lines = [
        f"{detail.id}  {detail.title}\n",
        f"  bucket       {bucket}\n",
        *under,
        *depends,
        *during,
        *filed_here,
        *supersede,
        *amends,
        *amended,
        *committed,
        *verified,
        *superseded,
        *removed,
        *described,
        *about,
        *(f"  {part:<13}{text}\n" for part, text in stated.items() if text),
        f"Tasks ({len(detail.tasks)})\n",
    ]
    for task in detail.tasks:
        lines.append(f"  {task.id}  {task.title}\n")
        task_bucket = next(name for name, states in BUCKETS if task.state in states)
        if task.state == BLOCKED:
            lines.append(f"    bucket           {task_bucket}, blocked\n")
            lines.append(f"    reason           {task.reason}\n")
            lines.append(f"    waiting on       {task.waiting_on}\n")
        elif task_bucket != "Backlog":
            lines.append(f"    bucket           {task_bucket}\n")
        if task.commit:
            lines.append(f"    commit           {task.commit}\n")
        lines.append(f"    expected output  {task.expected_output}\n")
        if task.description:
            lines.append(f"    description      {task.description}\n")
    return "".join([*lines, *_knowledge_lines(detail.knowledge)])
