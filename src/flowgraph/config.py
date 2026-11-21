"""The configuration of a record: the layers it turns on, kept as `config.toml` in the record.

The file holds a table per layer, each key with its default, so a record without the file holds
the defaults. The development -- the branch and the worktree of a start, the scoping of a branch,
the landing -- is off unless `[development] enabled = true`.
"""

import json
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

# The file of the configuration inside a record.
CONFIG = "config.toml"

# The key that turns the development on, as a refusal names it.
DEVELOPMENT_ENABLED = "development.enabled"


@dataclass(frozen=True)
class Development:
    """The development beside the source code: turned on, or off."""

    enabled: bool


@dataclass(frozen=True)
class Config:
    """The configuration of a record: one value per layer, each built from its table."""

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


class _DevelopmentTable(_Table):
    """What `[development]` holds; a key left out is its default."""

    enabled: bool = False


class _ConfigFile(_Table):
    """What the file holds: a table per layer; a table left out holds its defaults."""

    development: _DevelopmentTable = _DevelopmentTable()


# What the value of a key takes, by the type of the error pydantic reports of it.
_TAKES = {"bool_type": "true or false", "model_type": "a table"}


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
    value is of another type than the key takes, and when the text is no TOML.
    """
    try:
        held = _ConfigFile.model_validate(tomllib.loads(text))
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"no TOML: {error}") from error
    except ValidationError as error:
        raise ConfigError(_refusal(error)) from error
    return Config(development=Development(enabled=held.development.enabled))


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
