"""The refusals of a command: each is written as a usage error, whichever command raises it."""

from flowgraph.criterion import (
    CommitError,
    CommitNeededError,
    CriterionError,
    DecisionError,
    EmptyPartError,
)
from flowgraph.development import GateError, GitError, SlugError
from flowgraph.development.parallel import ParallelError
from flowgraph.development.release import ReleaseError
from flowgraph.development.scope import NotOnMainError, OutOfScopeError
from flowgraph.development.task_check import CheckError, TaskCheckError
from flowgraph.development.version import VersionError
from flowgraph.development.way import LandError
from flowgraph.feature import FeatureFileError, FeatureNotFoundError, NoCriterionError
from flowgraph.feature.item import OpenWorkItemError
from flowgraph.feature.start import FeatureNotStartedError, NoWorkItemError, WorkItemInProgressError
from flowgraph.graph import FormatError
from flowgraph.item.commands import ItemIdError
from flowgraph.knowledge.list import KindListedError
from flowgraph.parent import FeatureIdError
from flowgraph.record import ConfigError
from flowgraph.record.init import NoDirectoryError, RecordHeldError
from flowgraph.record.queue import NotInBacklogError, SameItemError, UnderFeatureError
from flowgraph.record.queue_file import QueueFileError
from flowgraph.relation import RelationError
from flowgraph.relation.depends import StartWaitsError
from flowgraph.relation.read import RelationReadError
from flowgraph.status import PaceError, StatusFormatError
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
from flowgraph.term.item import TermExistsError
from flowgraph.work_item import (
    NoPartError,
    NoSuchPartError,
    NotVerifiableError,
    RemovedAlreadyError,
    VerifiedAlreadyError,
    WorkItemFileError,
    WorkItemIdError,
    WorkItemNotFoundError,
)

# The refusals of a command, each written as a usage error; a git step refused among them, and
# a file of the record that holds no work item, no Feature or no queue (B-0019), and a relation
# that names nothing or closes a cycle when the record is read (S-0078), and making a record where
# one is held or in no directory (S-0082), and a release refused or of a version that is none
# (S-0091).
REFUSED = (
    RecordHeldError,
    NoDirectoryError,
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
    ReleaseError,
    VersionError,
    CheckError,
    TaskCheckError,
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
    NotVerifiableError,
    VerifiedAlreadyError,
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
    StatusFormatError,
    TermError,
    TermFileError,
    TermNotFoundError,
    TermExistsError,
)
