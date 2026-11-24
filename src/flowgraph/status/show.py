"""The text fgraph writes for one item whole: a work item with its Tasks, or a Feature."""

from collections.abc import Iterable, Sequence

from flowgraph.feature import CriterionRow, FeatureDetail, criteria_rows
from flowgraph.knowledge import KnowledgeRow, about_text, governs_text, mark_text, superseded_text
from flowgraph.status.buckets import BUCKETS
from flowgraph.story import StoryDetail, StoryRow
from flowgraph.upkeep import UpkeepDetail, UpkeepRow
from flowgraph.work_item import BLOCKED, ProgressRow


def _knowledge_lines(knowledge: Sequence[KnowledgeRow]) -> list[str]:
    """The knowledge lines under their heading, each with its kind, its date and its text.

    A line lists its mark, when it has one, before its terms; a superseded line ends with the
    refs of the lines that supersede it.

    There is no heading without a line.
    """
    if not knowledge:
        return []
    return [
        f"Knowledge ({len(knowledge)})\n",
        *(
            f"  {line.kind}  {line.noted.date().isoformat()}  {line.text}{mark_text(line.mark)}"
            f"{about_text(line.about)}{governs_text(line.governs)}"
            f"{superseded_text(line.superseded_by)}\n"
            for line in knowledge
        ),
    ]


def _progress_lines(progress: Sequence[ProgressRow]) -> list[str]:
    """The progress lines of the work item itself under their heading, each with its date.

    The lines of a Task are listed under that Task; there is no heading without a line.
    """
    own = [line for line in progress if line.task == ""]
    if not own:
        return []
    return [
        f"Progress ({len(own)})\n",
        *(f"  {line.noted.date().isoformat()}  {line.text}\n" for line in own),
    ]


def _criteria_lines(criteria: Sequence[CriterionRow]) -> list[str]:
    """The criteria under their heading: as their text alone, or met k of n with their work items.

    The met form is used once a work item names a criterion; each line of it reads the number,
    met or not met, the text and the ids of the work items that realize it, when there are any.
    """
    if not any(row.realized_by for row in criteria):
        return [f"Criteria ({len(criteria)})\n", *(f"  {row.text}\n" for row in criteria)]
    met = sum(row.met for row in criteria)
    lines = [f"Criteria ({len(criteria)}), met {met} of {len(criteria)}\n"]
    for row in criteria:
        mark = "met" if row.met else "not met"
        by = f"  {', '.join(row.realized_by)}" if row.realized_by else ""
        lines.append(f"  {row.number}  {mark:<7}  {row.text}{by}\n")
    return lines


def feature_text(detail: FeatureDetail, rows: Iterable[StoryRow | UpkeepRow], bucket: str) -> str:
    """The Feature with its bucket, its criteria, then its work items with their buckets.

    The bucket of a Feature is read from its state and its work items, so it is given; a
    commit and a description are listed only when there is one. A blocked Feature is listed in
    its bucket as blocked, with its reason and what it waits on; a removed one with its reason.
    Its criteria are listed as met k of n once a work item names one, each with the work items
    that realize it; met is a completed one, and a removed one is not counted.
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
        *_criteria_lines(criteria_rows(detail.criteria, listed)),
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
    A parent, the criterion of it that it realizes by its place and its text, or the words none
    of the criteria of the parent when it has none there, the work items it depends on each with
    its bucket, the work item it was filed
    during, the work items filed during it, the work items it supersedes, the completed one it
    amends, the work items that amend it, a description, an agent, a commit, the answer of its
    closing with its day and the text the run printed, the work item that supersedes a removed
    one and the reason of a removal are listed only when there is one, the bucket of a
    Task only once it has left Backlog. A blocked work item or Task is listed in InProgress as
    blocked, with its reason and what it waits on; a removed Task in Removed with its reason.
    The knowledge lines follow, in the order
    noted, each with its kind, its date and its text, then the terms it is about; a superseded
    line ends with the refs of the lines that supersede it; there is no heading without one.
    The progress lines of a Task follow its description, those of the work item follow the
    knowledge lines under Progress (n), each with its day and its text, in the order noted;
    there is no heading without one.
    The terms the item is about are listed after its description, only when there are some, and
    its complexity after them, only when it has one.
    """
    bucket = next(name for name, states in BUCKETS if detail.state in states)
    under = [f"  parent       {detail.parent}\n"] if detail.parent else []
    realized = detail.realized or f"none of the criteria of {detail.parent}"
    realizes = (
        [] if detail.realizes is None else [f"  realizes     {detail.realizes}  {realized}\n"]
    )
    waits = ", ".join(f"{each.id} ({each.bucket})" for each in detail.depends_on)
    depends = [f"  depends on   {waits}\n"] if waits else []
    during = [f"  filed during {detail.filed_during}\n"] if detail.filed_during else []
    here = ", ".join(detail.filed_here)
    filed_here = [f"  filed here   {here}\n"] if here else []
    amends = [f"  amends       {detail.amends}\n"] if detail.amends else []
    amending = ", ".join(detail.amended_by)
    amended = [f"  amended by   {amending}\n"] if amending else []
    handed = [f"  agent        {detail.agent}\n"] if detail.agent else []
    committed = [f"  commit       {detail.commit}\n"] if detail.commit else []
    answer = detail.verified
    day = None if answer is None else answer.on.date().isoformat()
    verified = [] if answer is None else [f"  verified     {answer.answer}  {day}  {answer.text}\n"]
    removed = [f"  reason       {detail.reason}\n"] if detail.reason else []
    waited = [f"  waiting on   {detail.waiting_on}\n"] if detail.waiting_on else []
    superseded = [f"  superseded by {detail.superseded_by}\n"] if detail.superseded_by else []
    supersedes = ", ".join(detail.supersedes)
    supersede = [f"  supersedes   {supersedes}\n"] if supersedes else []
    described = [f"  description  {detail.description}\n"] if detail.description else []
    about = [f"  about        {', '.join(detail.about)}\n"] if detail.about else []
    rated = [f"  complexity   {detail.complexity}\n"] if detail.complexity else []
    stated = {
        "given": detail.given,
        "when": detail.when,
        "then": detail.then,
        "observed": detail.observed,
        "expected": detail.expected,
        "hypothesis": detail.hypothesis,
        "decision": detail.decision,
        "answer": detail.answer,
    }
    lines = [
        f"{detail.id}  {detail.title}\n",
        f"  bucket       {bucket}{', blocked' if detail.waiting_on else ''}\n",
        *under,
        *realizes,
        *depends,
        *during,
        *filed_here,
        *supersede,
        *amends,
        *amended,
        *handed,
        *committed,
        *verified,
        *superseded,
        *removed,
        *waited,
        *described,
        *about,
        *rated,
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
            if task.reason:
                lines.append(f"    reason           {task.reason}\n")
        if task.commit:
            lines.append(f"    commit           {task.commit}\n")
        lines.append(f"    expected output  {task.expected_output}\n")
        if task.check:
            lines.append(f"    check            {task.check}\n")
        if task.description:
            lines.append(f"    description      {task.description}\n")
        for line in detail.progress:
            if line.task == task.id:
                lines.append(f"    progress         {line.noted.date().isoformat()}  {line.text}\n")
    return "".join([*lines, *_knowledge_lines(detail.knowledge), *_progress_lines(detail.progress)])
