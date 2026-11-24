"""What a config.toml may hold: a table per layer, each key with its type and its default.

Strict, so no value is read as another type; `flowgraph.record.config` builds the configuration
of it.
"""

from pydantic import BaseModel, ConfigDict, Field

from flowgraph.record.archive import ArchiveTable
from flowgraph.record.layers import Driver, Merge, Mode, TagAt


class _Table(BaseModel):
    """A table of the file: it takes the keys it names alone, each a value of its type as written.

    Strict, so that no value is read as another type: `"yes"` and `1` are no `true`.
    """

    model_config = ConfigDict(extra="forbid", strict=True)


class _GitTable(_Table):
    """What `[git]` holds; a key left out is its default."""

    commit: bool = True


class _DevelopmentTable(_Table):
    """What `[development]` holds; a key left out is its default."""

    enabled: bool = False
    parallel: int | None = Field(default=None, ge=1)
    # Not strict, so that the word of the file is read as the way of merging it names.
    merge: Merge = Field(default=Merge.MERGE_COMMIT, strict=False)
    # A text that holds a character other than a blank: an empty command line runs nothing.
    gate: str | None = Field(default=None, pattern=r"\S")
    # Not strict, so that the word of the file is read as the driver it names.
    driver: Driver = Field(default=Driver.DEVELOPER, strict=False)
    # Not strict, so that the word of the file is read as the mode it names.
    mode: Mode = Field(default=Mode.BRANCH, strict=False)
    # A whole number of days of 1 or more, then d: the age a branch passes before status says so.
    branch_max: str | None = Field(default=None, pattern=r"^[1-9][0-9]*d$")


class _DeliveryTable(_Table):
    """What `[delivery]` holds; a key left out is its default."""

    push: bool = False
    # Not strict, so that the word of the file is read as the closes it names.
    tag: TagAt = Field(default=TagAt.NONE, strict=False)


class ConfigFile(_Table):
    """What the file holds: a table per layer; a table left out holds its defaults."""

    git: _GitTable = _GitTable()
    development: _DevelopmentTable = _DevelopmentTable()
    delivery: _DeliveryTable = _DeliveryTable()
    archive: ArchiveTable = ArchiveTable()
