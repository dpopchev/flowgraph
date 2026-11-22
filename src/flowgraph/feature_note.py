"""The note of a Feature, beside that of a work item: `fgraph note` takes both.

A Feature keeps knowledge lines as a work item does, in any of its states; a Task keeps none. It
runs on the store of a record, as the commands of a work item do (`flowgraph.item`).
"""

from flowgraph.feature import note_feature
from flowgraph.feature_item import is_feature_id
from flowgraph.item import MESSAGE, Written, note_item
from flowgraph.knowledge import KnowledgeKind
from flowgraph.parent import feature_id_text, parse_feature_id
from flowgraph.record import Now
from flowgraph.store import Store


def note_named(
    item: str, kind: KnowledgeKind, text: str, store: Store, now: Now, about: tuple[str, ...] = ()
) -> Written:
    """Keep the line of that kind and text, about the terms given, on the Feature or work item.

    Returns what the write says. Raises FeatureNotFoundError when the record holds no such
    Feature and EmptyPartError when the text is blank; for any other id the refusal of
    `note_item`. Nothing is saved then.
    """
    if not is_feature_id(item):
        return note_item(item, kind, text, store, now, about)
    feature_id = parse_feature_id(item)
    note_feature(
        feature_id=feature_id,
        kind=kind,
        text=text,
        load_feature=store.features.load_feature,
        save_feature=store.features.save_feature,
        now=now,
        about=about,
    )
    named = feature_id_text(feature_id)
    return Written(f"noted {named}\n", MESSAGE.format(f"note {named}"))
