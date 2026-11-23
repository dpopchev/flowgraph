"""The configuration of a record: the layers it turns on, kept as `config.toml` in the record.

The file holds a table per layer, each key with its default, so a record without the file holds
the defaults. The commits fgraph makes of the writes of the record are on unless `[git] commit =
false`. The development -- the branch and the worktree of a start, the scoping of a branch, the
landing -- is off unless `[development] enabled = true`. The layers build on each other: the
branch of a work item carries its record, so the development needs the commits. `[development]
parallel` is the most work items started at once; it has no default, so left out nothing limits
them. `[development] merge` is how a landing merges: `merge-commit` unless it names `squash` or
`fast-forward`. `[development] gate` is the one command line a landing runs before main moves;
it has no default either, so left out a landing runs none. `[delivery] push = true` pushes main
once a landing is whole; it is false by default. `[delivery] tag = "feature-close"` tags main
with its next version once a landing completes a Feature; it is `none` by default. Each layer is
a value (`flowgraph.record.layers`); what a file refused says is `flowgraph.record.config_refusal`.
"""

import tomllib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

import tomli_w
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from flowgraph.record.config_refusal import refusal
from flowgraph.record.layers import (
    UNGATED,
    UNLIMITED,
    Delivery,
    Development,
    Gated,
    Git,
    Merge,
    Parallel,
    TagAt,
)

# The file of the configuration inside a record.
CONFIG = "config.toml"

# The key that turns the development on, as a refusal names it.
DEVELOPMENT_ENABLED = "development.enabled"

# The key that names the command a landing runs before main moves, as a refusal names it.
DEVELOPMENT_GATE = "development.gate"

# The key that says how a landing merges, as a refusal names it.
DEVELOPMENT_MERGE = "development.merge"

# The key that limits the work items started at once, as a refusal names it.
DEVELOPMENT_PARALLEL = "development.parallel"

# The key that turns the commits of the record off, as a refusal names it.
GIT_COMMIT = "git.commit"

# The key that pushes main once a landing is whole.
DELIVERY_PUSH = "delivery.push"

# The key that tags main at the close of a Feature.
DELIVERY_TAG = "delivery.tag"


@dataclass(frozen=True)
class Config:
    """The configuration of a record: one value per layer, each built from its table."""

    git: Git
    development: Development
    delivery: Delivery


# The configuration of the record in that directory; the defaults when it holds no config.toml.
LoadConfig = Callable[[Path], Config]

# The settings of a record: the keys its config.toml writes, each with its value, by table.
# Plain data: a key the file leaves out is left out, where the configuration holds its default.
Settings = Mapping[str, Mapping[str, object]]

# The settings of the record, whole; none when it holds no config.toml.
LoadSettings = Callable[[], Settings]

# Save the settings whole.
SaveSettings = Callable[[Settings], None]


class ConfigError(ValueError):
    """A config.toml that holds no configuration; names the table or the key refused."""


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


class _DeliveryTable(_Table):
    """What `[delivery]` holds; a key left out is its default."""

    push: bool = False
    # Not strict, so that the word of the file is read as the closes it names.
    tag: TagAt = Field(default=TagAt.NONE, strict=False)


class _ConfigFile(_Table):
    """What the file holds: a table per layer; a table left out holds its defaults."""

    git: _GitTable = _GitTable()
    development: _DevelopmentTable = _DevelopmentTable()
    delivery: _DeliveryTable = _DeliveryTable()


def make_config(text: str) -> Config:
    """The configuration the text of a config.toml holds; a key it leaves out is its default.

    Raises ConfigError naming the first table or key the configuration does not have, or whose
    value is of another type than the key takes, a count below 1, no way of merging, a blank
    gate or no word of a tag, and when the text is no TOML; naming both keys when it turns the
    development on with the commits off.
    """
    try:
        held = _ConfigFile.model_validate(tomllib.loads(text))
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"no TOML: {error}") from error
    except ValidationError as error:
        raise ConfigError(refusal(error)) from error
    if held.development.enabled and not held.git.commit:
        raise ConfigError(
            f"{DEVELOPMENT_ENABLED} is true while {GIT_COMMIT} is false:"
            " the development needs the commits of the record"
        )
    most = held.development.parallel
    command = held.development.gate
    development = Development(
        enabled=held.development.enabled,
        parallel=UNLIMITED if most is None else Parallel(most),
        merge=held.development.merge,
        gate=UNGATED if command is None else Gated(command),
    )
    delivery = Delivery(push=held.delivery.push, tag=held.delivery.tag)
    return Config(git=Git(commit=held.git.commit), development=development, delivery=delivery)


def make_settings(text: str) -> dict[str, dict[str, object]]:
    """The settings the text of a config.toml writes; a key it leaves out is left out.

    Raises ConfigError as make_config does: the settings are those of a configuration.
    """
    make_config(text)
    return tomllib.loads(text)


def settings_text(settings: Settings) -> str:
    """The text of the config.toml that writes the settings."""
    return tomli_w.dumps(settings)


def _read[Held](record: Path, make: Callable[[str], Held]) -> Held:
    """What make builds of the config.toml of the record, of no text when it holds no file.

    Raises ConfigError naming the file and the key when the file holds no configuration.
    """
    path = record / CONFIG
    if not path.is_file():
        return make("")
    try:
        return make(path.read_text(encoding="utf-8"))
    except ConfigError as error:
        raise ConfigError(f"{path}: {error}") from error


def read_config(record: Path) -> Config:
    """Adapter: the configuration of the record, the defaults when it holds no config.toml.

    Raises ConfigError naming the file and the key when the file holds no configuration.
    """
    return _read(record, make_config)


def read_settings(record: Path) -> dict[str, dict[str, object]]:
    """Adapter: the settings the config.toml of the record writes, none when it holds no file.

    Raises ConfigError naming the file and the key when the file holds no configuration.
    """
    return _read(record, make_settings)


def write_settings(record: Path, settings: Settings) -> None:
    """Adapter: write the settings as the config.toml of the record.

    The file is written beside its path and read back through make_config before it replaces
    it. Raises ConfigError naming the key when the settings hold no configuration; the file is
    then as it was, and a record without one is left without.
    """
    path = record / CONFIG
    beside = path.with_name(f"{path.name}.tmp")
    beside.write_text(settings_text(settings), encoding="utf-8")
    try:
        make_config(beside.read_text(encoding="utf-8"))
    except ConfigError:
        beside.unlink()
        raise
    beside.replace(path)
