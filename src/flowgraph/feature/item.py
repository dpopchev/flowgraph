"""A Feature named by its id: its add, its view over its work items, and the parent it gives.

Each runs on the store of a record, as the commands of a work item do (`flowgraph.item.commands`).
"""

import re
from collections.abc import Iterable
from dataclasses import replace
from typing import assert_never

from flowgraph.criterion import (
    NO_COMMIT,
    CommitError,
    Evidence,
    evidence_text,
    evidence_written,
)
from flowgraph.feature import (
    DONE,
    BlockedFeature,
    CompletedFeature,
    Feature,
    FeatureRemovedError,
    RemovedFeature,
    StartedFeature,
    add_feature,
    completed_feature,
    feature_bucket,
    feature_detail,
)
from flowgraph.item.commands import MESSAGE, Written
from flowgraph.item.id import ItemIdError, parse_shown_id
from flowgraph.knowledge.supersede import superseded_rows
from flowgraph.parent import (
    STANDALONE,
    FeatureId,
    Parent,
    feature_id_text,
    parse_feature_id,
)
from flowgraph.record import Now
from flowgraph.record.queue import Placed
from flowgraph.record.store import Store
from flowgraph.relation.depends import bucketed
from flowgraph.status import (
    BACKLOG,
    backlog_as_added,
    feature_text,
    in_show_order,
    rows_under,
    show_text,
)
from flowgraph.status.show_document import (
    JSON,
    TEXT,
    chosen_show_format,
    feature_json,
    work_item_json,
)
from flowgraph.task import CompletedAlreadyError
from flowgraph.term import is_term_name
from flowgraph.term.document import term_json
from flowgraph.term.item import term_shown, term_text
from flowgraph.work_item import WorkItemId, WorkItemRow


class OpenWorkItemError(ValueError):
    """A Feature to complete that holds a work item neither completed nor removed."""


def is_feature_id(text: str) -> bool:
    """True when the text is written as the id of a Feature: `F-` and a number.

    A number below 1 is written so too, so `F-0000` goes to the Feature, whose parse refuses it.
    """
    return re.fullmatch(r"F-\d+", text) is not None


def add_feature_item(
    title: str,
    criteria: Iterable[str],
    description: str,
    store: Store,
    now: Now,
    about: tuple[str, ...] = (),
) -> Written:
    """Add a Feature with its criteria, about the terms given; what the write says.

    Raises EmptyPartError when the title or a criterion is blank and NoCriterionError when it
    states none; nothing is saved.
    """
    added = add_feature(
        title=title,
        criteria=criteria,
        description=description,
        find_feature_ids=store.features.find_feature_ids,
        save_feature=store.features.save_feature,
        now=now,
        about=about,
    )
    text = feature_id_text(added)
    return Written(f"added {text}\n", MESSAGE.format(f"add {text}"))


def show_feature_item(feature: str, store: Store, format_: str = TEXT) -> str:
    """The text of the Feature of that id: its criteria, then its work items with their buckets.

    Its bucket is that of its own state over the states of those work items, as a list shows
    it. They are listed by kind and number, those in Backlog among them in the order the queue
    gives: the one they start in. The format is json for its JSON document, else its text.
    Raises FeatureIdError when the text is no Feature id and FeatureNotFoundError when the
    record holds no such Feature.
    """
    feature_id = parse_feature_id(feature)
    shown = store.features.load_feature(feature_id)
    detail = feature_detail(shown)
    detail = replace(detail, knowledge=superseded_rows(detail.id, detail.knowledge, store))
    held = rows_under(feature_id, store)
    rows = in_show_order(held, backlog_as_added(held), store.load_queue())
    bucket = feature_bucket(shown, [row.state for row in rows])
    if format_ == JSON:
        return feature_json(detail, rows, bucket)
    return feature_text(detail, rows, bucket)


def _shown_id(item: str) -> Placed:
    """The id fgraph show reads in the text; its refusal says a term name would do as well."""
    try:
        return parse_shown_id(item)
    except ItemIdError as error:
        raise ItemIdError(f"{error} nor the name of a term") from None


def show_any_item(item: str, store: Store, format_: str = TEXT) -> str:
    """What fgraph show gives of the term of that name, or the work item or Feature of that id.

    The format is text or json, chosen first, before anything is read. Raises ShowFormatError
    naming both when it is neither, TermNotFoundError for a term name the record holds none of,
    FeatureIdError for a Feature id below 1, ItemIdError for a text that is neither, and the
    refusal of the record for an id it holds no item of. ItemIdError says the term too.
    """
    chosen = chosen_show_format(format_)
    if is_term_name(item):
        shown = term_shown(item, store)
        return term_json(shown) if chosen == JSON else term_text(shown)
    match _shown_id(item):
        case FeatureId():
            return show_feature_item(item, store, chosen)
        case WorkItemId() as work_item:
            detail = bucketed(store.find_work_item_detail(work_item), store)
            return work_item_json(detail) if chosen == JSON else show_text(detail)
        case _ as unreachable:
            assert_never(unreachable)


def _last_commit(rows: Iterable[WorkItemRow]) -> Evidence:
    """The commit of the work item completed last among the rows; none when none is completed."""
    completed = [(row.completed, row.commit) for row in rows if row.completed is not None]
    return evidence_written(max(completed)[1]) if completed else NO_COMMIT


def complete_feature_item(feature: str, commit: str | None, store: Store, now: Now) -> Written:
    """Complete the started Feature of that id, each work item of it completed or removed.

    It is completed now, in the commit of its last completed work item, none when none is: the
    way to Completed of a Feature whose last work item was removed, which no completion of a
    work item completes. Raises FeatureIdError when the text is no Feature id, CommitError when
    a commit is given, FeatureNotFoundError when the record holds no such Feature, the refusal
    of its completion when it is in Backlog, completed or removed, and OpenWorkItemError naming
    the first work item of it neither completed nor removed. Nothing is saved then.
    """
    feature_id = parse_feature_id(feature)
    named = feature_id_text(feature_id)
    if commit is not None:
        last = "it is completed at the commit of its last completed work item"
        raise CommitError(f"{named} takes no --commit: {last}")
    held = store.features.load_feature(feature_id)
    rows = list(rows_under(feature_id, store).values())
    done = completed_feature(held, now(), _last_commit(rows))
    open_rows = [row for row in rows if row.state not in DONE]
    if open_rows:
        where = "in Backlog" if open_rows[0].state == BACKLOG else open_rows[0].state
        raise OpenWorkItemError(f"{named} cannot complete: {open_rows[0].id} is {where}")
    store.features.save_feature(done)
    sha = evidence_text(done.commit)
    at = f" at {sha}" if sha else ""
    return Written(f"completed {named}{at}\n", MESSAGE.format(f"complete {named}"))


def parent_named(parent: str | None, store: Store) -> Parent:
    """The parent a work item is added under: standing alone when none is named.

    Raises FeatureIdError when the name is no Feature id, FeatureNotFoundError when the record
    holds no such Feature, CompletedAlreadyError when that Feature is completed and
    RemovedAlreadyError when it is removed.
    """
    if parent is None:
        return STANDALONE
    feature_id = parse_feature_id(parent)
    match store.features.load_feature(feature_id):
        case Feature() | StartedFeature() | BlockedFeature():
            return feature_id
        case CompletedFeature():
            raise CompletedAlreadyError(f"{feature_id_text(feature_id)} is completed already")
        case RemovedFeature():
            raise FeatureRemovedError(feature_id)
        case _ as unreachable:
            assert_never(unreachable)
