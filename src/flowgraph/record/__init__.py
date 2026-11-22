"""The record of a project: where it lives, its configuration and the store of its files.

Its location and its configuration are named here. The store, the journal of its writes, the
Backlog queue and the settings command read and write the items of a record, which take their
clock and their directory from this package, so each is imported from its own module: store,
journal, queue, queue_file and setting.
"""

from flowgraph.record.config import (
    CONFIG,
    DELIVERY_PUSH,
    DEVELOPMENT_ENABLED,
    DEVELOPMENT_GATE,
    DEVELOPMENT_MERGE,
    DEVELOPMENT_PARALLEL,
    GIT_COMMIT,
    Config,
    ConfigError,
    LoadConfig,
    Settings,
    make_config,
    read_config,
)
from flowgraph.record.layers import Gate, Gated, Merge, Parallel, Ungated, Unlimited
from flowgraph.record.location import (
    ITEMS,
    NAMES,
    Found,
    Given,
    GivenMissing,
    IsDir,
    Location,
    Missing,
    NotFound,
    Now,
    locate,
)

__all__ = [
    "CONFIG",
    "DELIVERY_PUSH",
    "DEVELOPMENT_ENABLED",
    "DEVELOPMENT_GATE",
    "DEVELOPMENT_MERGE",
    "DEVELOPMENT_PARALLEL",
    "GIT_COMMIT",
    "ITEMS",
    "NAMES",
    "Config",
    "ConfigError",
    "Found",
    "Gate",
    "Gated",
    "Given",
    "GivenMissing",
    "IsDir",
    "LoadConfig",
    "Location",
    "Merge",
    "Missing",
    "NotFound",
    "Now",
    "Parallel",
    "Settings",
    "Ungated",
    "Unlimited",
    "locate",
    "make_config",
    "read_config",
]
