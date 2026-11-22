"""The refusals of a command: each is written as a usage error, whichever command raises it."""

from flowgraph.branch import GitError, SlugError
from flowgraph.config import ConfigError
from flowgraph.criterion import (
    CommitError,
    CommitNeededError,
    CriterionError,
    DecisionError,
    EmptyPartError,
)
from flowgraph.feature import FeatureFileError, FeatureNotFoundError, NoCriterionError
from flowgraph.feature.item import OpenWorkItemError
from flowgraph.feature.start import FeatureNotStartedError, NoWorkItemError, WorkItemInProgressError
from flowgraph.gate import GateError
from flowgraph.graph import FormatError
from flowgraph.item import ItemIdError
from flowgraph.item_depends import StartWaitsError
from flowgraph.knowledge_list import KindListedError
from flowgraph.land import LandError
from flowgraph.parallel import ParallelError
from flowgraph.parent import FeatureIdError
from flowgraph.queue import NotInBacklogError, QueueFileError, SameItemError, UnderFeatureError
from flowgraph.relation import RelationError
from flowgraph.relation_read import RelationReadError
from flowgraph.scope import NotOnMainError, OutOfScopeError
from flowgraph.task import (
    BlockedError,
    CompletedAlreadyError,
    ItemInBacklogError,
    NoTaskError,
    NotBlockedError,
    NotStartedError,
    OpenTaskError,
    StartedAlreadyError,
    TaskIdError,
    TaskInProgressError,
    TaskNotFoundError,
)
from flowgraph.term import TermError, TermFileError, TermNotFoundError
from flowgraph.term_item import TermExistsError
from flowgraph.watch import PaceError
from flowgraph.work_item import (
    NoPartError,
    NoSuchPartError,
    RemovedAlreadyError,
    WorkItemFileError,
    WorkItemIdError,
    WorkItemNotFoundError,
)

# The refusals of a command, each written as a usage error; a git step refused among them, and
# a file of the record that holds no work item, no Feature or no queue (B-0019), and a relation
# that names nothing or closes a cycle when the record is read (S-0078).
REFUSED = (
    ConfigError,
    WorkItemFileError,
    FeatureFileError,
    QueueFileError,
    ItemIdError,
    WorkItemIdError,
    FeatureIdError,
    FeatureNotFoundError,
    NoCriterionError,
    NoWorkItemError,
    FeatureNotStartedError,
    WorkItemInProgressError,
    SlugError,
    GitError,
    LandError,
    GateError,
    NotOnMainError,
    ParallelError,
    OutOfScopeError,
    CommitError,
    CommitNeededError,
    EmptyPartError,
    CriterionError,
    DecisionError,
    NoPartError,
    NoSuchPartError,
    RemovedAlreadyError,
    WorkItemNotFoundError,
    TaskIdError,
    TaskNotFoundError,
    NoTaskError,
    NotStartedError,
    StartedAlreadyError,
    BlockedError,
    NotBlockedError,
    TaskInProgressError,
    ItemInBacklogError,
    OpenTaskError,
    OpenWorkItemError,
    CompletedAlreadyError,
    NotInBacklogError,
    SameItemError,
    UnderFeatureError,
    RelationError,
    RelationReadError,
    StartWaitsError,
    PaceError,
    KindListedError,
    FormatError,
    TermError,
    TermFileError,
    TermNotFoundError,
    TermExistsError,
)
