"""The relations of a work item as its file holds them: the ids as written, in order.

The work items it depends on, the one it was filed during and the one it amends.
"""

from collections.abc import Iterable, Sequence

from pydantic import BaseModel

from flowgraph.relation import Relations, make_relations
from flowgraph.work_item.id import (
    Kind,
    WorkItemId,
    WorkItemIdError,
    parse_work_item_id,
    work_item_id_text,
)


class RelationsFile(BaseModel):
    """What the file of a work item holds of its relations, each held only when there is one."""

    depends_on: list[str] = []
    filed_during: str = ""
    amends: str = ""


def id_held(text: str, kinds: Sequence[Kind]) -> WorkItemId:
    """The id of a work item of one of the kinds written as the text.

    Raises WorkItemIdError naming the text when it is the id of none of them.
    """
    for kind in kinds:
        try:
            return parse_work_item_id(kind, text)
        except WorkItemIdError:
            continue
    nouns = ", ".join(kind.noun for kind in kinds)
    raise WorkItemIdError(f"relation {text!r} is the id of no work item of a kind known: {nouns}")


def relations_held(
    item_id: WorkItemId, held: RelationsFile, kinds: Sequence[Kind]
) -> Relations[WorkItemId]:
    """The relations of the work item a validated file holds, built through their constructor.

    Raises WorkItemIdError when an id is that of no kind given and RelationError when the item
    names itself.
    """
    depends_on: Iterable[WorkItemId] = (id_held(text, kinds) for text in held.depends_on)
    filed_during = id_held(held.filed_during, kinds) if held.filed_during else None
    amends = id_held(held.amends, kinds) if held.amends else None
    return make_relations(item_id, depends_on, filed_during, amends)


def relations_primitives(relations: Relations[WorkItemId]) -> dict[str, object]:
    """The relations as the primitives a file holds: each held only when there is one."""
    ids = [work_item_id_text(each) for each in relations.depends_on]
    depends = {"depends_on": ids} if ids else {}
    named = relations.filed_during
    during = {"filed_during": work_item_id_text(named)} if named else {}
    amended = relations.amends
    amends = {"amends": work_item_id_text(amended)} if amended else {}
    return {**depends, **during, **amends}
