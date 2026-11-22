"""The relations a work item names to other work items, and the record checked against them.

The relations are named here. What a command asks of them and their check as the record is read
run on the store of a record, whose work items hold their relations through this package, so each
is imported from its own module: depends and read.
"""

from flowgraph.relation.model import (
    RelationError,
    Relations,
    Standing,
    Waited,
    amended_by,
    closes_cycle,
    depended_on_by,
    make_relations,
    superseding,
    waiting_for,
    with_depends_on,
)

__all__ = [
    "RelationError",
    "Relations",
    "Standing",
    "Waited",
    "amended_by",
    "closes_cycle",
    "depended_on_by",
    "make_relations",
    "superseding",
    "waiting_for",
    "with_depends_on",
]
