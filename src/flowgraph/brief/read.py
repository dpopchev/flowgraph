"""The brief of a work item, read from the record and from git: the shell of the brief."""

from pathlib import Path

from flowgraph.brief.document import JSON, brief_json, chosen_brief_format
from flowgraph.brief.model import Brief, FeatureBrief, TermLine, governing
from flowgraph.brief.not_named import not_named_document, not_named_of
from flowgraph.brief.text import brief_text
from flowgraph.development.commit import OpenGit, kept_in
from flowgraph.feature import feature_bucket, feature_detail
from flowgraph.item.id import parse_work_item_id_of_any_kind
from flowgraph.knowledge.list import collected, live_entries, newest_first
from flowgraph.parent import parse_feature_id
from flowgraph.record.store import Store
from flowgraph.relation.depends import bucketed
from flowgraph.status import rows_under
from flowgraph.work_item import WorkItemId, work_item_id_text


def _held_by_git(
    item: WorkItemId, record: Path, open_git: OpenGit
) -> tuple[str | None, Path | None]:
    """The branch `wi/<id>-*` of the work item and the worktree it is checked out in.

    The first branch with a worktree, else the first branch; none for either git holds none of.
    A record outside a git work tree, or one git ignores, has neither.
    """
    work_tree = kept_in(record, open_git)
    if work_tree is None:
        return None, None
    branches = work_tree.find_branches(f"wi/{work_item_id_text(item)}-*")
    placed = [(branch, work_tree.find_worktree(branch)) for branch in branches]
    return next(
        ((branch, path) for branch, path in placed if path is not None),
        (branches[0], None) if branches else (None, None),
    )


def _feature_of(text: str, store: Store) -> tuple[FeatureBrief, list[str]]:
    """The Feature of that id and the terms it is about.

    Its bucket is read from its state and from the states of its work items.
    """
    feature_id = parse_feature_id(text)
    held = store.features.load_feature(feature_id)
    states = [row.state for row in rows_under(feature_id, store).values()]
    detail = feature_detail(held)
    brief = FeatureBrief(
        detail.id,
        feature_bucket(held, states),
        detail.title,
        detail.description,
        tuple(detail.knowledge),
    )
    return brief, detail.about


def brief_of(item: str, store: Store, record: Path, open_git: OpenGit) -> Brief:
    """The brief of the work item of that id, in any state.

    Raises WorkItemIdError naming every kind when the text is the id of none, such as that of a
    Feature or of a Task, and WorkItemNotFoundError when the record holds no such work item.
    Nothing is written.
    """
    item_id = parse_work_item_id_of_any_kind(item)
    detail = bucketed(store.find_work_item_detail(item_id), store)
    feature, feature_about = _feature_of(detail.parent, store) if detail.parent else (None, [])
    governed = tuple(governing(newest_first(live_entries(collected(store)), None), detail.tasks))
    names = dict.fromkeys(
        [*detail.about, *feature_about, *(name for entry in governed for name in entry.about)]
    )
    branch, worktree = _held_by_git(item_id, record, open_git)
    return Brief(
        detail,
        branch,
        worktree,
        feature,
        governed,
        tuple(TermLine(name, store.terms.load_term(name).meaning) for name in names),
    )


def brief_output(
    item: str,
    format_: str,
    store: Store,
    record: Path,
    open_git: OpenGit,
    *,
    not_named: bool = False,
) -> str:
    """The brief of the work item of that id in that format, text or JSON.

    The format is chosen before anything is read. With not_named, the files changed and not
    committed that the brief of its started Task does not name are printed in its place, in the
    same format. Raises BriefFormatError naming both formats when it is neither, the refusals of
    `brief_of` and, with not_named, NotNamedError of `not_named_of`: no started Task, or a
    record outside a git work tree. Nothing is written.
    """
    chosen = chosen_brief_format(format_)
    brief = brief_of(item, store, record, open_git)
    if not_named:
        return not_named_document(not_named_of(brief, record, open_git), chosen)
    return brief_json(brief) if chosen == JSON else brief_text(brief)
