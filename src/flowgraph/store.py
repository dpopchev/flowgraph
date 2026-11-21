"""The store of a record: its reads and writes, each bound to its directory, kept as its files.

The kinds of work item a record holds are listed here, once.
"""

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from flowgraph import work_item
from flowgraph.journal import Change, changed_files, noted, restore
from flowgraph.queue import QUEUE, LoadQueue, Queue, SaveQueue, read_queue, write_queue
from flowgraph.record import ITEMS
from flowgraph.story import STORY
from flowgraph.upkeep import UPKEEP
from flowgraph.work_item import (
    FindTaskIds,
    Kind,
    LoadWorkItem,
    SaveWorkItem,
    WorkItemDetail,
    WorkItemId,
    WorkItemRow,
    WorkItemState,
    work_item_id_text,
)

# The kinds of work item a record holds, in the order fgraph reads them.
KINDS: tuple[Kind, ...] = (STORY, UPKEEP)

# The rows of the work items of that kind in the record; an empty list when it holds none.
FindKindRows = Callable[[Kind], list[WorkItemRow]]

# The work item of that id as plain data; raises WorkItemNotFoundError when the record holds none.
FindWorkItemDetail = Callable[[WorkItemId], WorkItemDetail]

# The files of the record written since the store was opened whose content changed.
FindChangedFiles = Callable[[], list[Path]]

# Put every file written since the store was opened back as it was before.
RestoreFiles = Callable[[], object]


@dataclass(frozen=True)
class Store:
    """The reads and writes of one record, each already bound to its directory."""

    find_work_item_rows: FindKindRows
    load_work_item: LoadWorkItem
    find_work_item_detail: FindWorkItemDetail
    find_task_ids: FindTaskIds
    save_work_item: SaveWorkItem
    load_queue: LoadQueue
    save_queue: SaveQueue
    find_changed_files: FindChangedFiles
    restore_files: RestoreFiles


# The store of the record in that directory.
OpenStore = Callable[[Path], Store]


def read_every_task_id(record: Path) -> list[str]:
    """Adapter: the ids of every Task of every kind in the record, as written, in no order."""
    return [task for kind in KINDS for task in work_item.read_task_ids(record, kind)]


def work_item_file(record: Path, item_id: WorkItemId) -> Path:
    """The path of the file of the work item of that id in the record."""
    return record / ITEMS / f"{work_item_id_text(item_id)}.toml"


def open_files(record: Path) -> Store:
    """The store of the record in that directory, kept as its files.

    It journals each file before it writes it, so it names the files a write changed and puts
    them back as they were.
    """
    journal: list[Change] = []

    def save_work_item(item: WorkItemState) -> None:
        nonlocal journal
        journal = noted(journal, work_item_file(record, item.id))
        work_item.write_work_item(record, item)

    def save_queue(queue: Queue) -> None:
        nonlocal journal
        journal = noted(journal, record / QUEUE)
        write_queue(record, KINDS, queue)

    return Store(
        find_work_item_rows=partial(work_item.read_work_item_rows, record),
        load_work_item=partial(work_item.read_work_item, record),
        find_work_item_detail=partial(work_item.read_work_item_detail, record),
        find_task_ids=partial(read_every_task_id, record),
        save_work_item=save_work_item,
        load_queue=partial(read_queue, record, KINDS),
        save_queue=save_queue,
        find_changed_files=lambda: changed_files(journal),
        restore_files=lambda: restore(journal),
    )
