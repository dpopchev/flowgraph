"""The file of an Upkeep in the record: the work item file, read by the `U-` prefix."""

from collections.abc import Callable
from pathlib import Path

from flowgraph import work_item
from flowgraph.upkeep.model import UPKEEP, UpkeepDetail, UpkeepId, UpkeepRow, UpkeepState

# The rows of the upkeeps in the record at the path; an empty list when it holds none.
ReadUpkeepRows = Callable[[Path], list[UpkeepRow]]

# The Upkeep of that id in the record at the path, whole; raises UpkeepNotFoundError when the
# record holds none.
ReadUpkeep = Callable[[Path, UpkeepId], UpkeepState]

# The Upkeep of that id in the record at the path, with its Tasks, as plain data; raises
# UpkeepNotFoundError when the record holds none.
ReadUpkeepDetail = Callable[[Path, UpkeepId], UpkeepDetail]

# The ids of every Task in the record at the path, as written; an empty list when it holds none.
ReadTaskIds = Callable[[Path], list[str]]

# Save the Upkeep whole into the record at the path.
WriteUpkeep = Callable[[Path, UpkeepState], None]

read_upkeep = work_item.read_work_item
read_upkeep_detail = work_item.read_work_item_detail
write_upkeep = work_item.write_work_item


def read_upkeep_rows(record: Path) -> list[UpkeepRow]:
    """Adapter: the rows of the upkeeps in the record, by id; a file of another kind is left alone.

    Raises UpkeepFileError naming the first file of an Upkeep that does not hold one.
    """
    return work_item.read_work_item_rows(record, UPKEEP)


def read_task_ids(record: Path) -> list[str]:
    """Adapter: the ids of every Task of the upkeeps in the record, as written, in no order.

    Raises UpkeepFileError naming the first file of an Upkeep that does not hold one.
    """
    return work_item.read_task_ids(record, UPKEEP)
