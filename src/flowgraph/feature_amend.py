"""The amendment of a Feature, beside that of a work item: `fgraph amend` takes both.

A Feature is to its work items what a work item is to its Tasks: the wording of one in Backlog
is rewritten, part by part. It is not a move: the state of the Feature stays, and so do its id,
its created time, its work items and its place in the queue. It runs on the store of a record,
as the commands of a work item do (`flowgraph.item`).
"""

from collections.abc import Sequence
from dataclasses import dataclass, fields
from typing import assert_never

from flowgraph.feature import (
    BlockedFeature,
    CompletedFeature,
    Feature,
    FeatureState,
    StartedFeature,
    make_feature,
)
from flowgraph.feature_item import is_feature_id
from flowgraph.item import MESSAGE, Written, amend_item, parse_work_item_id_of_any_kind
from flowgraph.parent import feature_id_text, parse_feature_id
from flowgraph.store import Store
from flowgraph.task import BlockedError, CompletedAlreadyError, StartedAlreadyError
from flowgraph.work_item import Amendment, NoPartError, NoSuchPartError, work_item_id_text


@dataclass(frozen=True)
class FeatureAmendment:
    """The parts of a Feature to rewrite: each its new text, or None where it stays as it was.

    Its criteria are rewritten whole: the ones given replace the ones it had.
    """

    title: str | None = None
    description: str | None = None
    criteria: tuple[str, ...] | None = None


def amended_feature(feature: FeatureState, amendment: FeatureAmendment) -> Feature:
    """The Feature in Backlog with the parts the amendment names rewritten, the rest as it was.

    Each part goes through the constructor of a Feature. Raises NoPartError when it names none,
    EmptyPartError when its title or a criterion is blank, NoCriterionError when it gives no
    criterion in place of the ones it had, StartedAlreadyError when the Feature is started,
    BlockedError when it is blocked and CompletedAlreadyError when it is completed.
    """
    named = feature_id_text(feature.id)
    match feature:
        case Feature():
            if amendment == FeatureAmendment():
                raise NoPartError(f"amend rewrites no part of {named}: name one")
            title, described, criteria = amendment.title, amendment.description, amendment.criteria
            return make_feature(
                feature.id,
                feature.title if title is None else title,
                feature.criteria if criteria is None else criteria,
                feature.description if described is None else described,
                feature.created,
            )
        case StartedFeature():
            raise StartedAlreadyError(f"{named} is started already")
        case BlockedFeature():
            raise BlockedError(f"{named} is blocked")
        case CompletedFeature():
            raise CompletedAlreadyError(f"{named} is completed already")
        case _ as unreachable:
            assert_never(unreachable)


def _of_feature(named: str, parts: Amendment, criteria: Sequence[str] | None) -> FeatureAmendment:
    """The amendment of the Feature of that name the parts of an amend and its criteria state.

    Every part of an amend but its title and its description is one of a work item. Raises
    NoSuchPartError naming the ones given.
    """
    taken = {part.name for part in fields(FeatureAmendment)}
    foreign = [
        part.name
        for part in fields(parts)
        if part.name not in taken and getattr(parts, part.name) is not None
    ]
    if foreign:
        listed = ", ".join(foreign)
        only = "a Feature is amended by its title, its description and its criteria"
        raise NoSuchPartError(f"{named} has no {listed}: {only}")
    stated = None if criteria is None else tuple(criteria)
    return FeatureAmendment(parts.title, parts.description, stated)


def amend_named(
    item: str, parts: Amendment, criteria: Sequence[str] | None, store: Store
) -> Written:
    """Rewrite the parts named of the Feature or the work item in Backlog of that id.

    Returns what the write says. The criteria are those of a Feature, given in place of the
    ones it had; the other parts of its amendment are its title and its description. Raises
    NoSuchPartError when a part of a work item is given to a Feature or criteria to a work
    item, FeatureNotFoundError when the record holds no such Feature, or the refusal of its
    amend; for any other id the refusal of `amend_item`. Nothing is saved.
    """
    if not is_feature_id(item):
        if criteria is not None:
            named = work_item_id_text(parse_work_item_id_of_any_kind(item))
            raise NoSuchPartError(f"{named} has no criteria: only a Feature states them")
        return amend_item(item, parts, store)
    feature_id = parse_feature_id(item)
    named = feature_id_text(feature_id)
    amendment = _of_feature(named, parts, criteria)
    store.features.save_feature(amended_feature(store.features.load_feature(feature_id), amendment))
    return Written(f"amended {named}\n", MESSAGE.format(f"amend {named}"))
