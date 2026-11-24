"""The amendment of a Feature, beside that of a work item: `fgraph amend` takes both.

It takes a Task in Backlog too, by its id, through `amend_task_item`, which refuses a part no
Task has and a Task that is started, blocked, completed or removed.

A Feature is to its work items what a work item is to its Tasks: its wording is rewritten, part
by part, in Backlog as it is and once started with its deviation. It is not a move: the state of
the Feature stays, and so do its id, its created time, its work items and its place in the queue.
It runs on the store of a record, as the commands of a work item do (`flowgraph.item.commands`).
"""

from collections.abc import Sequence
from dataclasses import dataclass, fields, replace
from typing import assert_never

from flowgraph.feature import (
    BlockedFeature,
    CompletedFeature,
    Feature,
    FeatureRemovedError,
    FeatureState,
    RemovedFeature,
    StartedFeature,
    make_feature,
    noted_feature,
)
from flowgraph.feature.item import is_feature_id
from flowgraph.item.amend import amend_task_item
from flowgraph.item.commands import MESSAGE, Written, amend_item
from flowgraph.item.id import is_task_id, parse_amended_id
from flowgraph.knowledge import KnowledgeLine
from flowgraph.parent import feature_id_text, parse_feature_id
from flowgraph.record.store import Store
from flowgraph.task import CompletedAlreadyError
from flowgraph.work_item import (
    Amendment,
    DeviationError,
    NoPartError,
    NoSuchPartError,
    check_deviation,
    work_item_id_text,
)


@dataclass(frozen=True)
class FeatureAmendment:
    """The parts of a Feature to rewrite: each its new text, or None where it stays as it was.

    Its criteria are rewritten whole: the ones given replace the ones it had, and so are the
    terms it is about.
    """

    title: str | None = None
    description: str | None = None
    criteria: tuple[str, ...] | None = None
    about: tuple[str, ...] | None = None


def _rewritten[F: Feature | StartedFeature | BlockedFeature](
    feature: F, amendment: FeatureAmendment
) -> F:
    """The Feature with the parts the amendment names rewritten, each through make_feature.

    Raises NoPartError when it names none, EmptyPartError when its title or a criterion is blank
    and NoCriterionError when it gives no criterion in place of the ones it had.
    """
    if amendment == FeatureAmendment():
        raise NoPartError(f"amend rewrites no part of {feature_id_text(feature.id)}: name one")
    title, described, criteria = amendment.title, amendment.description, amendment.criteria
    checked = make_feature(
        feature.id,
        feature.title if title is None else title,
        feature.criteria if criteria is None else criteria,
        feature.description if described is None else described,
        feature.created,
    )
    about = feature.about if amendment.about is None else amendment.about
    return replace(
        feature,
        title=checked.title,
        description=checked.description,
        criteria=checked.criteria,
        about=about,
    )


def amended_feature(
    feature: FeatureState, amendment: FeatureAmendment, deviation: KnowledgeLine | None = None
) -> Feature | StartedFeature | BlockedFeature:
    """The Feature with the parts the amendment names rewritten, the rest as it was.

    One in Backlog is amended without a deviation; a started or blocked one with it, kept on it
    after the lines it had, in the state it had. Each part goes through the constructor of a
    Feature. Raises NoPartError when it names none, EmptyPartError when its title or a criterion
    is blank, NoCriterionError when it gives no criterion in place of the ones it had,
    DeviationError when a started Feature has none or one in Backlog has one,
    CompletedAlreadyError when it is completed and RemovedAlreadyError when it is removed.
    """
    named = feature_id_text(feature.id)
    match feature:
        case Feature():
            check_deviation(named, False, deviation)
            return _rewritten(feature, amendment)
        case StartedFeature() | BlockedFeature():
            check_deviation(named, True, deviation)
            amended = _rewritten(feature, amendment)
            return amended if deviation is None else noted_feature(amended, deviation)
        case CompletedFeature():
            raise CompletedAlreadyError(f"{named} is completed already")
        case RemovedFeature():
            raise FeatureRemovedError(feature.id)
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
    return FeatureAmendment(parts.title, parts.description, stated, parts.about)


def amend_named(
    item: str,
    parts: Amendment,
    criteria: Sequence[str] | None,
    store: Store,
    deviation: KnowledgeLine | None = None,
) -> Written:
    """Rewrite the parts named of the Feature, the work item or the Task in Backlog of that id.

    Returns what the write says. The criteria are those of a Feature, given in place of the
    ones it had; the other parts of its amendment are its title and its description. A started
    Feature or work item is amended with its deviation, kept on it in the same save. A Task
    takes its title, output, check and description alone: the refusals of `amend_task_item`, and
    no deviation. Raises NoSuchPartError when a part of a work item is given to a Feature or
    criteria to a work item, DeviationError when a deviation is given for a Task,
    FeatureNotFoundError when the record holds no such Feature, or the refusal of its amend; for
    any other id the refusal of `amend_item`. Nothing is saved.
    """
    if is_task_id(item):
        if deviation is not None:
            raise DeviationError(f"{item} takes no --deviation: a Task keeps no knowledge line")
        return amend_task_item(item, parts, criteria, store)
    if not is_feature_id(item):
        if criteria is not None:
            named = work_item_id_text(parse_amended_id(item))
            raise NoSuchPartError(f"{named} has no criteria: only a Feature states them")
        return amend_item(item, parts, store, deviation)
    feature_id = parse_feature_id(item)
    named = feature_id_text(feature_id)
    amendment = _of_feature(named, parts, criteria)
    was = store.features.load_feature(feature_id)
    store.features.save_feature(amended_feature(was, amendment, deviation))
    return Written(f"amended {named}\n", MESSAGE.format(f"amend {named}"))
