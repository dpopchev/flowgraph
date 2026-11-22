"""The store of a record: its reads and writes, each bound to its directory, kept as its files.

The kinds of work item a record holds are listed here, once.
"""

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Never

from flowgraph import work_item
from flowgraph.bug import BUG
from flowgraph.config import (
    CONFIG,
    LoadSettings,
    SaveSettings,
    Settings,
    read_settings,
    write_settings,
)
from flowgraph.feature import (
    FeatureNotFoundError,
    FeatureState,
    FindFeatureIds,
    LoadFeature,
    SaveFeature,
    feature_file,
    read_feature,
    read_feature_ids,
    write_feature,
)
from flowgraph.journal import Change, changed_files, noted, restore
from flowgraph.parent import FeatureId
from flowgraph.queue import QUEUE, LoadQueue, Queue, SaveQueue, read_queue, write_queue
from flowgraph.spike import SPIKE
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
)

# The kinds of work item a record holds, in the order fgraph reads them.
KINDS: tuple[Kind, ...] = (STORY, UPKEEP, BUG, SPIKE)

# The rows of the work items of that kind in the record; an empty list when it holds none.
FindKindRows = Callable[[Kind], list[WorkItemRow]]

# The work item of that id as plain data; raises WorkItemNotFoundError when the record holds none.
FindWorkItemDetail = Callable[[WorkItemId], WorkItemDetail]

# The files of the record written since the store was opened whose content changed.
FindChangedFiles = Callable[[], list[Path]]

# Put every file written since the store was opened back as it was before.
RestoreFiles = Callable[[], object]


@dataclass(frozen=True)
class FeatureStore:
    """The reads and writes of the Features of one record."""

    load_feature: LoadFeature
    save_feature: SaveFeature
    find_feature_ids: FindFeatureIds


class NoFeatureStoreError(Exception):
    """A Feature saved into a store that was built without the Features of its record."""


def _hold_none(feature_id: FeatureId) -> Never:
    """The load of a store that holds no Feature."""
    raise FeatureNotFoundError(feature_id)


def _take_none(feature: FeatureState) -> Never:
    """The save of a store that takes no Feature."""
    raise NoFeatureStoreError(f"this store keeps no Feature: {feature.title!r} is not saved")


# The Features of a store built without them: it holds none and takes none.
NO_FEATURES = FeatureStore(_hold_none, _take_none, list)


class NoSettingsStoreError(Exception):
    """Settings saved into a store that was built without the settings of its record."""


def _take_no_settings(settings: Settings) -> Never:
    """The save of a store that takes no settings."""
    raise NoSettingsStoreError("this store keeps no settings")


@dataclass(frozen=True)
class Store:
    """The reads and writes of one record, each already bound to its directory.

    A store built without its Features holds none, and so does one built without its settings.
    """

    find_work_item_rows: FindKindRows
    load_work_item: LoadWorkItem
    find_work_item_detail: FindWorkItemDetail
    find_task_ids: FindTaskIds
    save_work_item: SaveWorkItem
    load_queue: LoadQueue
    save_queue: SaveQueue
    find_changed_files: FindChangedFiles
    restore_files: RestoreFiles
    features: FeatureStore = NO_FEATURES
    load_settings: LoadSettings = dict
    save_settings: SaveSettings = _take_no_settings


# The store of the record in that directory.
OpenStore = Callable[[Path], Store]


def read_every_task_id(record: Path) -> list[str]:
    """Adapter: the ids of every Task of every kind in the record, as written, in no order."""
    return [task for kind in KINDS for task in work_item.read_task_ids(record, kind)]


def open_files(record: Path) -> Store:
    """The store of the record in that directory, kept as its files.

    It journals each file before it writes it, so it names the files a write changed and puts
    them back as they were.
    """
    journal: list[Change] = []

    def save_work_item(item: WorkItemState) -> None:
        nonlocal journal
        journal = noted(journal, work_item.work_item_path(record, item.id))
        work_item.write_work_item(record, item)

    def save_queue(queue: Queue) -> None:
        nonlocal journal
        journal = noted(journal, record / QUEUE)
        write_queue(record, KINDS, queue)

    def save_feature(feature: FeatureState) -> None:
        nonlocal journal
        journal = noted(journal, feature_file(record, feature.id))
        write_feature(record, feature)

    def save_settings(settings: Settings) -> None:
        nonlocal journal
        journal = noted(journal, record / CONFIG)
        write_settings(record, settings)

    features = FeatureStore(
        partial(read_feature, record), save_feature, partial(read_feature_ids, record)
    )
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
        features=features,
        load_settings=partial(read_settings, record),
        save_settings=save_settings,
    )
