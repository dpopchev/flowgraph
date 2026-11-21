"""The configuration of a record: the layers it turns on, kept as `config.toml` in the record.

The file holds a table per layer, each key with its default, so a record without the file holds
the defaults. The commits fgraph makes of the writes of the record are on unless `[git] commit =
false`. The development -- the branch and the worktree of a start, the scoping of a branch, the
landing -- is off unless `[development] enabled = true`. The layers build on each other: the
branch of a work item carries its record, so the development needs the commits. `[development]
parallel` is the most work items started at once; it has no default, so left out nothing limits
them. `[development] merge` is how a landing merges: `merge-commit` unless it names `squash` or
`fast-forward`. `[development] gate` is the one command line a landing runs before main moves;
it has no default either, so left out a landing runs none.
"""

import json
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

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


@dataclass(frozen=True)
class Git:
    """The commits of the record: fgraph commits every write of it, or none."""

    commit: bool


@dataclass(frozen=True)
class Parallel:
    """The most work items started at once: a whole number of 1 or more."""

    most: int


@dataclass(frozen=True)
class Unlimited:
    """No limit of the work items started at once: a value of the limit, not a missing one."""


# The one value of no limit.
UNLIMITED = Unlimited()

# How many work items are started at once: at most that many, or as many as are started.
Limit = Parallel | Unlimited


class Merge(Enum):
    """How a landing merges the branch of a work item into main; each is its word in the file."""

    MERGE_COMMIT = "merge-commit"
    SQUASH = "squash"
    FAST_FORWARD = "fast-forward"


@dataclass(frozen=True)
class Gated:
    """The gate of a landing: one command line, run through the shell, never a blank one."""

    command: str


@dataclass(frozen=True)
class Ungated:
    """No gate of a landing: a value of the gate, not a missing one."""


# The one value of no gate.
UNGATED = Ungated()

# What a landing runs before main moves: that command, or nothing.
Gate = Gated | Ungated


@dataclass(frozen=True)
class Development:
    """The development beside the source code: turned on, or off, and its keys as written.

    The limit, the merge and the gate are keys of the development: none says anything while it
    is off.
    """

    enabled: bool
    parallel: Limit
    merge: Merge
    gate: Gate


@dataclass(frozen=True)
class Config:
    """The configuration of a record: one value per layer, each built from its table."""

    git: Git
    development: Development


# The configuration of the record in that directory; the defaults when it holds no config.toml.
LoadConfig = Callable[[Path], Config]


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


class _ConfigFile(_Table):
    """What the file holds: a table per layer; a table left out holds its defaults."""

    git: _GitTable = _GitTable()
    development: _DevelopmentTable = _DevelopmentTable()


# What a count takes, whether its value is no whole number or one below 1.
_COUNT = "a whole number of 1 or more"

# What a way of merging takes: one of the words of Merge.
_WORDS = [merge.value for merge in Merge]
_WAY = f"{', '.join(_WORDS[:-1])} or {_WORDS[-1]}"

# What a gate takes, whether its value is no text or a blank one.
_COMMAND = "a command line"

# What the value of a key takes, by the type of the error pydantic reports of it.
_TAKES = {
    "bool_type": "true or false",
    "model_type": "a table",
    "int_type": _COUNT,
    "greater_than_equal": _COUNT,
    "enum": _WAY,
    "string_type": _COMMAND,
    "string_pattern_mismatch": _COMMAND,
}


def _refusal(error: ValidationError) -> str:
    """What the first error of a file refused says: its key, dotted, and why it is refused."""
    first = error.errors()[0]
    key = ".".join(str(part) for part in first["loc"])
    if first["type"] == "extra_forbidden":
        return f"{key} is no {'table' if len(first['loc']) == 1 else 'key'} of the configuration"
    written = json.dumps(first["input"], default=str)
    takes = _TAKES.get(first["type"])
    return f"{key} is {written}: {first['msg'] if takes is None else f'it takes {takes}'}"


def make_config(text: str) -> Config:
    """The configuration the text of a config.toml holds; a key it leaves out is its default.

    Raises ConfigError naming the first table or key the configuration does not have, or whose
    value is of another type than the key takes, a count below 1, no way of merging or a blank
    gate, and when the text is no TOML; naming both keys when it turns the development on with
    the commits off.
    """
    try:
        held = _ConfigFile.model_validate(tomllib.loads(text))
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"no TOML: {error}") from error
    except ValidationError as error:
        raise ConfigError(_refusal(error)) from error
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
    return Config(git=Git(commit=held.git.commit), development=development)


def read_config(record: Path) -> Config:
    """Adapter: the configuration of the record, the defaults when it holds no config.toml.

    Raises ConfigError naming the file and the key when the file holds no configuration.
    """
    path = record / CONFIG
    if not path.is_file():
        return make_config("")
    try:
        return make_config(path.read_text(encoding="utf-8"))
    except ConfigError as error:
        raise ConfigError(f"{path}: {error}") from error
