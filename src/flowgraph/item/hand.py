"""The hand of a started work item to an agent, named by its id: what the write says."""

from flowgraph.item.commands import MESSAGE, Written
from flowgraph.item.id import parse_work_item_id_of_any_kind
from flowgraph.record.store import Store
from flowgraph.work_item import work_item_id_text
from flowgraph.work_item.agent import make_agent
from flowgraph.work_item.handed import hand_work_item


def hand_item(item: str, agent: str, store: Store) -> Written:
    """Hand the started work item of that id to the agent, in place of the one it held.

    Raises WorkItemIdError when the text is the id of no work item, AgentError when the agent
    is no agent, or the refusal of the hand; nothing is saved.
    """
    item_id = parse_work_item_id_of_any_kind(item)
    handed = make_agent(agent)
    hand_work_item(
        item_id=item_id,
        agent=handed,
        load_work_item=store.load_work_item,
        save_work_item=store.save_work_item,
    )
    text = work_item_id_text(item_id)
    return Written(
        f"handed {text} to {handed.name}\n", MESSAGE.format(f"hand {text} to {handed.name}")
    )
