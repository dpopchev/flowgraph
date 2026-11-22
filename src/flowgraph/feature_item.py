"""A Feature named by its id: its add, its view over its work items, and the parent it gives.

Each runs on the store of a record, as the commands of a work item do (`flowgraph.item`).
"""

import re
from collections.abc import Iterable
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
from flowgraph.item import MESSAGE, Written, show_item
from flowgraph.item_id import parse_shown_id
from flowgraph.parent import (
    STANDALONE,
    FeatureId,
    Parent,
    feature_id_text,
    parse_feature_id,
)
from flowgraph.queue import queued
from flowgraph.record import Now
from flowgraph.status import BACKLOG, backlog_as_added, rows_under
from flowgraph.store import Store
from flowgraph.task import CompletedAlreadyError
from flowgraph.term import is_term_name
from flowgraph.term_item import show_term
from flowgraph.text import feature_text
from flowgraph.work_item import WorkItemId, WorkItemRow


class OpenWorkItemError(ValueError):
    """A Feature to complete that holds a work item neither completed nor removed."""


def is_feature_id(text: str) -> bool:
    """True when the text is written as the id of a Feature: `F-` and a number.

    A number below 1 is written so too, so `F-0000` goes to the Feature, whose parse refuses it.
    """
    return re.fullmatch(r"F-\d+", text) is not None


def add_feature_item(
    title: str, criteria: Iterable[str], description: str, store: Store, now: Now
) -> Written:
    """Add a Feature with its criteria; what the write says.

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
    )
    text = feature_id_text(added)
    return Written(f"added {text}\n", MESSAGE.format(f"add {text}"))


def show_feature_item(feature: str, store: Store) -> str:
    """The text of the Feature of that id: its criteria, then its work items with their buckets.

    Its bucket is that of its own state over the states of those work items, as a list shows
    it. They are listed by kind and number, those in Backlog among them in the order the queue
    gives: the one they start in. Raises FeatureIdError when the text is no Feature id and
    FeatureNotFoundError when the record holds no such Feature.
    """
    feature_id = parse_feature_id(feature)
    shown = store.features.load_feature(feature_id)
    detail = feature_detail(shown)
    held = rows_under(feature_id, store)
    in_backlog = backlog_as_added(held)
    start_order = queued(store.load_queue(), in_backlog)
    next_started = iter(sorted(in_backlog, key=start_order.index))
    rows = [held[next(next_started)] if row.state == BACKLOG else row for row in held.values()]
    return feature_text(detail, rows, feature_bucket(shown, [row.state for row in rows]))


def show_any_item(item: str, store: Store) -> str:
    """The text fgraph show gives of the term of that name, or the work item or Feature of that id.

    Raises TermNotFoundError for a term name the record holds none of, FeatureIdError for a
    Feature id below 1, ItemIdError for a text that is neither, and the refusal of `show_item` or
    of `show_feature_item` for an id the record holds no item of.
    """
    if is_term_name(item):
        return show_term(item, store)
    match parse_shown_id(item):
        case FeatureId():
            return show_feature_item(item, store)
        case WorkItemId():
            return show_item(item, store)
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
