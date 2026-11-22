"""The work items a work item depends on, as its file holds them: the ids as written, in order."""

from collections.abc import Iterable, Sequence

from flowgraph.relation import Relations, make_relations
from flowgraph.work_item.model import (
    Kind,
    WorkItemId,
    WorkItemIdError,
    parse_work_item_id,
    work_item_id_text,
)


def _id_held(text: str, kinds: Sequence[Kind]) -> WorkItemId:
    """The id of a work item of one of the kinds written as the text.

    Raises WorkItemIdError naming the text when it is the id of none of them.
    """
    for kind in kinds:
        try:
            return parse_work_item_id(kind, text)
        except WorkItemIdError:
            continue
    nouns = ", ".join(kind.noun for kind in kinds)
    raise WorkItemIdError(f"depends_on {text!r} is the id of no work item of a kind known: {nouns}")


def relations_held(
    item_id: WorkItemId, depends_on: Iterable[str], kinds: Sequence[Kind]
) -> Relations[WorkItemId]:
    """The relations of the work item a validated file holds, built through their constructor.

    Raises WorkItemIdError when an id is that of no kind given and RelationError when the item
    names itself.
    """
    return make_relations(item_id, (_id_held(text, kinds) for text in depends_on))


def depends_primitives(relations: Relations[WorkItemId]) -> dict[str, object]:
    """The relations as the primitives a file holds: held only when there is one."""
    ids = [work_item_id_text(each) for each in relations.depends_on]
    return {"depends_on": ids} if ids else {}
