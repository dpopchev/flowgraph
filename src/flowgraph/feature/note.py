"""The note of a work item and of a Feature: `fgraph note` takes both.

A Feature keeps knowledge lines as a work item does, in any of its states; a Task keeps none. It
runs on the store of a record, as the commands of a work item do (`flowgraph.item.commands`).
"""

from flowgraph import work_item
from flowgraph.feature import note_feature
from flowgraph.feature.item import is_feature_id
from flowgraph.item.commands import MESSAGE, Written
from flowgraph.item.id import parse_work_item_id_of_any_kind
from flowgraph.knowledge import UNMARKED, KnowledgeKind, Mark
from flowgraph.parent import feature_id_text, parse_feature_id
from flowgraph.record import Now
from flowgraph.record.store import Store
from flowgraph.work_item import work_item_id_text


def note_item(
    item: str,
    kind: KnowledgeKind,
    text: str,
    store: Store,
    now: Now,
    about: tuple[str, ...] = (),
    governs: tuple[str, ...] = (),
    mark: Mark = UNMARKED,
    supersedes: tuple[str, ...] = (),
) -> Written:
    """Keep the line of that kind and text, about the terms given, on the work item of that id.

    It governs the files given, is kept with the mark given and the refs of the lines it
    supersedes, in any state, after the lines the item keeps already, none of which is amended:
    neither is a line it supersedes. Raises WorkItemIdError when the text is the id
    of no kind, WorkItemNotFoundError when the record holds no such item and EmptyPartError when
    the text is blank; nothing is saved.
    """
    item_id = parse_work_item_id_of_any_kind(item)
    work_item.note_work_item(
        item_id=item_id,
        kind=kind,
        text=text,
        load_work_item=store.load_work_item,
        save_work_item=store.save_work_item,
        now=now,
        about=about,
        governs=governs,
        mark=mark,
        supersedes=supersedes,
    )
    named = work_item_id_text(item_id)
    return Written(f"noted {named}\n", MESSAGE.format(f"note {named}"))


def note_named(
    item: str,
    kind: KnowledgeKind,
    text: str,
    store: Store,
    now: Now,
    about: tuple[str, ...] = (),
    governs: tuple[str, ...] = (),
    mark: Mark = UNMARKED,
    supersedes: tuple[str, ...] = (),
) -> Written:
    """Keep the line of that kind and text, about the terms given, on the Feature or work item.

    It governs the files given and is kept with the mark given and the refs of the lines it
    supersedes, in the file of that item alone. Returns what the write says. Raises
    FeatureNotFoundError when the record holds no such Feature and EmptyPartError when the
    text is blank; for any other id the refusal of `note_item`. Nothing is saved then.
    """
    if not is_feature_id(item):
        return note_item(item, kind, text, store, now, about, governs, mark, supersedes)
    feature_id = parse_feature_id(item)
    note_feature(
        feature_id=feature_id,
        kind=kind,
        text=text,
        load_feature=store.features.load_feature,
        save_feature=store.features.save_feature,
        now=now,
        about=about,
        governs=governs,
        mark=mark,
        supersedes=supersedes,
    )
    named = feature_id_text(feature_id)
    return Written(f"noted {named}\n", MESSAGE.format(f"note {named}"))
