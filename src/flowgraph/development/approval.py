"""Who approves a landing: `[development] approver` of the configuration.

Under developer a landing waits for the developer, who tells fgraph by the flag --approved of
fgraph land; the flag is the word, and nothing of it is written in the record.
"""

from typing import assert_never

from flowgraph.item.id import parse_work_item_id_of_any_kind
from flowgraph.record import Config
from flowgraph.record.config import DEVELOPMENT_APPROVER
from flowgraph.record.layers import Approver, branched
from flowgraph.work_item import WorkItemIdError, work_item_id_text

# The refusal of a landing held for the developer, with the id of the work item in both places.
HELD = (
    "{id} cannot land: "
    + DEVELOPMENT_APPROVER
    + " = developer, the landing waits for the developer"
    " -- run fgraph land {id} --approved once the developer approves it"
)


class ApprovalError(Exception):
    """A landing held for the developer: names the work item and the key."""


def check_approved(item: str, approved: bool, config: Config) -> None:
    """Return when the landing of the item may go on; raise ApprovalError when it waits.

    Nothing is read from the record or from git: the flag, the development, the approver and the
    text of the item decide it, in that order. The development off and the trunk are left to the
    landing, which refuses them in its own words.
    """
    if approved:
        return
    if not branched(config.development):
        return
    match config.development.approver:
        case Approver.AGENT:
            return
        case Approver.DEVELOPER:
            pass
        case _ as unreachable:
            assert_never(unreachable)
    try:
        item_id = parse_work_item_id_of_any_kind(item)
    except WorkItemIdError:
        return
    raise ApprovalError(HELD.format(id=work_item_id_text(item_id)))
