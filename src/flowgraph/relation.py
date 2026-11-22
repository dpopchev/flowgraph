"""The relations a work item names to other work items: a typed reference, stored on the item.

A relation is stored on the item that names it and never on the item it names: the other side is
derived by a view over the record, so a write stays one file. The relations of an item are one
value with a field per kind of relation, so a new kind is a new field. The first is `depends_on`:
the work items it waits for, none by default.

A relation holds the ids of the items it names whatever their type, so this module needs no work
item: the views read the record as plain data.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Relations[Id]:
    """What a work item names: the ids of the work items it depends on, in the order given."""

    depends_on: tuple[Id, ...] = ()


class RelationError(ValueError):
    """A relation refused: a work item that names itself, or one that closes a cycle."""


@dataclass(frozen=True)
class Standing:
    """A work item of the record as the views of a relation read it: plain data.

    Its bucket as it is listed, whether it is completed, and the ids it depends on as written.
    """

    bucket: str
    completed: bool
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class Waited:
    """A work item another one still waits for, with the bucket it is listed in."""

    id: str
    bucket: str


def make_relations[Id](item: Id, depends_on: Iterable[Id] = ()) -> Relations[Id]:
    """The relations of that work item: each work item it depends on once, in the order given.

    Raises RelationError when it names itself.
    """
    named = tuple(dict.fromkeys(depends_on))
    if item in named:
        raise RelationError(f"{item} cannot depend on itself")
    return Relations(named)


def with_depends_on[Id](
    relations: Relations[Id], item: Id, depends_on: Iterable[Id]
) -> Relations[Id]:
    """The relations with the ids the item depends on replaced by those given, the rest as it was.

    None given takes them all away. Raises RelationError when the item names itself.
    """
    return replace(relations, depends_on=make_relations(item, depends_on).depends_on)


def waiting_for(item: str, record: Mapping[str, Standing]) -> list[Waited]:
    """The work items the item depends on that are not completed, each with its bucket.

    It is what a start still waits for: none once every one is completed. Reads the ids the
    item names from the record; an item the record does not hold waits for nothing.
    """
    standing = record.get(item)
    if standing is None:
        return []
    held = [(named, record[named]) for named in standing.depends_on if named in record]
    return [Waited(named, there.bucket) for named, there in held if not there.completed]


def closes_cycle(item: str, depends_on: Sequence[str], record: Mapping[str, Standing]) -> bool:
    """True when the item depending on those ids would close a cycle in the record.

    It does when one of them depends on the item, directly or through others. The item naming
    itself is no cycle here: the constructor of its relations refuses it.
    """
    pending = [named for named in depends_on if named != item]
    seen: set[str] = set()
    while pending:
        named = pending.pop()
        if named == item:
            return True
        if named in seen or named not in record:
            continue
        seen.add(named)
        pending.extend(record[named].depends_on)
    return False
