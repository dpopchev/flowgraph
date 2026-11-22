"""A Feature named by its id: its add, its view over its work items, and the parent it gives.

Each runs on the store of a record, as the commands of a work item do (`flowgraph.item`).
"""

from collections.abc import Iterable

from flowgraph.feature import add_feature, feature_bucket, feature_detail
from flowgraph.item import MESSAGE, Written
from flowgraph.parent import (
    STANDALONE,
    FeatureIdError,
    Parent,
    feature_id_text,
    parse_feature_id,
)
from flowgraph.queue import queued
from flowgraph.record import Now
from flowgraph.status import BACKLOG, backlog_as_added, rows_by_id
from flowgraph.store import Store
from flowgraph.text import feature_text


def is_feature_id(text: str) -> bool:
    """True when the text is written as the id of a Feature."""
    try:
        parse_feature_id(text)
    except FeatureIdError:
        return False
    return True


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
    shown = store.features.load_feature(parse_feature_id(feature))
    detail = feature_detail(shown)
    held = {item_id: row for item_id, row in rows_by_id(store).items() if row.parent == detail.id}
    in_backlog = backlog_as_added(held)
    start_order = queued(store.load_queue(), in_backlog)
    next_started = iter(sorted(in_backlog, key=start_order.index))
    rows = [held[next(next_started)] if row.state == BACKLOG else row for row in held.values()]
    return feature_text(detail, rows, feature_bucket(shown, [row.state for row in rows]))


def parent_named(parent: str | None, store: Store) -> Parent:
    """The parent a work item is added under: standing alone when none is named.

    Raises FeatureIdError when the name is no Feature id and FeatureNotFoundError when the
    record holds no such Feature.
    """
    if parent is None:
        return STANDALONE
    feature_id = parse_feature_id(parent)
    store.features.load_feature(feature_id)
    return feature_id
